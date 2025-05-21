from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse, Response
from curl_cffi.requests.exceptions import (
    CurlError,
    ContentDecodingError,
    StreamConsumedError,
)
from schemas import ProxyRequest, BROWSER_TYPES, API_KEY_EXPECTED
from utils import pick_impersonate, perform_final_hop, forward_to_next_hop, render_response

app = FastAPI(title="Proxy Chain Service", version="1.1.0")


def check_key(apikey: str | None):
    if API_KEY_EXPECTED and apikey != API_KEY_EXPECTED:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid API key")


@app.post("/proxy", summary="单跳代理")
async def proxy(req: ProxyRequest):
    check_key(req.apikey)
    imp = pick_impersonate(req.impersonate)
    try:
        resp = await perform_final_hop(req, imp)
    except (CurlError, ContentDecodingError, StreamConsumedError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return render_response(resp, imp, req.return_data, req.stream)


@app.post("/looproxy", summary="链式代理")
async def looproxy(req: ProxyRequest):
    """
    * proxy_chain 为空     -> 等价 /proxy
    * proxy_chain 非空     -> 取首元素作为下一跳 URL，递归 POST
    """
    check_key(req.apikey)
    imp = pick_impersonate(req.impersonate)

    # ---------- 无链路：落地 ----------
    if not req.proxy_chain:
        try:
            resp = await perform_final_hop(req, imp)
        except (CurlError, ContentDecodingError, StreamConsumedError) as e:
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        return render_response(resp, imp, req.return_data, req.stream)

    # ---------- 有链路：转发 ----------
    next_hop, *rest = req.proxy_chain
    nested_req = req.copy(update={"proxy_chain": rest})

    try:
        resp = await forward_to_next_hop(next_hop, nested_req, imp)
    except (CurlError, ContentDecodingError, StreamConsumedError) as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    hop_by_hop = {"content-encoding", "transfer-encoding", "content-length", "connection"}
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in hop_by_hop}

    if req.stream:
        return StreamingResponse(resp.iter_content(), status_code=resp.status_code, media_type="application/octet-stream", headers=headers)

    hop_by_hop = {"content-length", "transfer-encoding"}
    headers = {k: v for k, v in resp.headers.items() if k.lower() not in hop_by_hop}
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=headers,
        media_type=resp.headers.get("content-type")
    )


@app.get("/impersonate", summary="impersonate 可用列表")
def impersonate():
    return JSONResponse(content=BROWSER_TYPES)


@app.get("/health", summary="健康状态")
def health():
    return JSONResponse(content={"status": "healthy"})


if __name__ == "__main__":
    import os, platform, uvicorn

    config = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": int(os.getenv("PROXY_API_KEY", "8000")),
        "proxy_headers": True,
        "forwarded_allow_ips": "*",
        "access_log": False,
    }
    if platform.system().lower() != "windows":
        config.update({"loop": "uvloop", "http": "httptools"})
    uvicorn.run(**config)
