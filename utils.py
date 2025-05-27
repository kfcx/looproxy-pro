import json
import secrets
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool
import curl_cffi.requests as curl
from curl_cffi import CurlOpt
from schemas import ProxyRequest, BROWSER_TYPES, HTTPMethod


def pick_impersonate(user_choice):
    """校验或随机挑一个浏览器指纹"""
    if user_choice:
        if user_choice not in BROWSER_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Unsupported impersonate={user_choice}")
        return user_choice

    return secrets.choice(BROWSER_TYPES)


def build_curl_opts(timeout_ms: int):
    """常用超时：总超时 + 连接超时（≤5s 或总超时的较小值）"""
    return {
        CurlOpt.TIMEOUT_MS: timeout_ms,
        CurlOpt.CONNECTTIMEOUT_MS: min(timeout_ms, 5_000),
    }


async def perform_final_hop(req: ProxyRequest, impersonate: str):
    """
    真正把请求发到目标站点的最后一跳。
    依旧放在线程池里执行，确保 uvloop 事件循环无阻塞
    """
    return await run_in_threadpool(
        curl.request,
        method=req.method.value,
        url=str(req.url),
        params=req.params,
        headers=req.headers,
        cookies=req.cookies,
        json=req.data if req.method in {"POST", "PUT", "PATCH"} else None,
        data=req.data if req.method not in {"POST", "PUT", "PATCH"} else None,
        stream=req.stream,
        impersonate=impersonate,
        proxies=req.proxies,
        curl_options=build_curl_opts(req.timeout_ms),
    )


async def forward_to_next_hop(
        next_url: str, nested_req: ProxyRequest, impersonate: str
):
    """
    把当前 JSON 负载 POST 给链路中的下一台代理服务。
    使用 curl_cffi 直接 POST；对方再继续递归或最终落地。
    """
    return await run_in_threadpool(
        curl.request,
        method=HTTPMethod.POST,
        url=next_url,
        headers={"Content-Type": "application/json"},
        json=json.loads(nested_req.json()),
        stream=nested_req.stream,
        impersonate=impersonate,
        curl_options=build_curl_opts(nested_req.timeout_ms),
    )


def render_response(resp: curl.Response, impersonate: str, include_body: bool, stream: bool):
    """统一把 curl.Response 转成 FastAPI Response"""
    meta = {
        "status_code": resp.status_code,
        "url": resp.url,
        "elapsed": resp.elapsed,
        "headers": dict(resp.headers),
        "cookies": resp.cookies.get_dict(),
        "impersonate": impersonate,
    }

    if not include_body:
        return JSONResponse(content=meta, status_code=resp.status_code)

    if stream:
        return StreamingResponse(resp.iter_content(), status_code=resp.status_code, media_type="application/octet-stream", headers=meta["headers"])

    ctype = resp.headers.get("Content-Type", "")
    if ctype.startswith("application/json"):
        meta["data"] = resp.json()
    elif ctype.startswith("text/"):
        meta["data"] = resp.text
    else:
        meta["data"] = resp.content.hex()

    return JSONResponse(content=meta, status_code=resp.status_code)
