FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY index.html .
COPY dashboard.html .
COPY calendar.html .
COPY categories.html .
COPY recurring.html .
COPY account.html .
COPY heatmap.html .
COPY accounts.html .
COPY settings.html .
COPY reports.html .
COPY rules.html .
COPY guide.html .
COPY changelog.html .
COPY goals.html .
COPY owed.html .
COPY today.html .
COPY family.html .
COPY subscriptions.html .
COPY forecast.html .
COPY debt.html .
COPY insights.html .
COPY budget.html .
COPY zakat.html .
COPY wealth.html .
COPY soon.html .
COPY rail.js .
COPY face.css .
COPY face.js .
COPY hakim-grotesk.woff2 .
COPY scripts/ ./scripts/

EXPOSE 8001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
