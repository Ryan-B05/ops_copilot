import logging

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from text_to_sql import ask, get_database_connection

logger = logging.getLogger("opscopilot")

app = FastAPI(
    title="Ops Copilot API",
    description=(
        "Natural language business questions converted "
        "into validated read only PostgreSQL queries."
    ),
    version="1.0.0",
)


class QuestionRequest(BaseModel):
    question: str = Field(
        ..., min_length=1, description="Business question to ask Ops Copilot"
    )


@app.get("/")
def root():
    return {"service": "Ops Copilot", "status": "running", "version": "1.0.0"}


@app.get("/health")
def health():
    connection = None
    cursor = None

    try:
        connection = get_database_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT 1;")
        result = cursor.fetchone()

        if result != (1,):
            raise HTTPException(status_code=503, detail="Database health check failed.")

        return {"status": "healthy", "database": "connected"}

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(status_code=503, detail="Database connection unavailable.")

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


@app.post("/ask")
def ask_question(request: QuestionRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = ask(question)

    except Exception:
        # keep the details in the server log, not in the response
        logger.exception("Ops Copilot processing failed")

        raise HTTPException(status_code=500, detail="Ops Copilot processing failed.")

    if result["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail={"status": result["status"], "message": result["message"]},
        )

    response = {
        "status": result["status"],
        "question": result["question"],
        "answer": result["answer"],
        "generated_sql": result["generated_sql"],
        "validated_sql": result["validated_sql"],
        "columns": result["columns"],
        "rows": result["rows"],
        "message": result["message"],
    }

    return jsonable_encoder(response)
