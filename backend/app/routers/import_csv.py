from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CSVImportResult
from app.services.csv_importer import import_odds_csv

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/csv", response_model=CSVImportResult)
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = (await file.read()).decode("utf-8-sig")
    return import_odds_csv(db, content)
