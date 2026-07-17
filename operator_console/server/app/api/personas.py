from fastapi import APIRouter

router = APIRouter()


@router.get("")
def personas_list():
    return {"ok": True, "personas": []}


@router.get("/operational")
def personas_operational():
    return {"ok": True, "personas": []}
