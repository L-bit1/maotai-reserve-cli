from fastapi import APIRouter

from . import accounts, app_release, auth, jobs, logs, lottery, mobile, payments, products, records, settings, shops

api_router = APIRouter()
api_router.include_router(app_release.router)
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(accounts.router)
api_router.include_router(products.router)
api_router.include_router(shops.router)
api_router.include_router(jobs.router)
api_router.include_router(records.router)
api_router.include_router(lottery.router)
api_router.include_router(payments.router)
api_router.include_router(logs.router)
api_router.include_router(mobile.router)
