FROM python:3.12-slim@sha256:090ba77e2958f6af52a5341f788b50b032dd4ca28377d2893dcf1ecbdfdfe203
WORKDIR /workspace
COPY deploy/api/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock && \
    useradd --uid 10001 --create-home app && mkdir -p /var/lib/zhi-heng && chown app:app /var/lib/zhi-heng
COPY app /workspace/app
COPY prompts /workspace/prompts
COPY scripts /workspace/scripts
COPY examples /workspace/examples
COPY NOTICE.md THIRD_PARTY_NOTICES.md /licenses/
ENV PROJECT_ROOT=/workspace PYTHONUNBUFFERED=1 LOG_CONSOLE_ENABLE=False LOG_FILE_ENABLE=False \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live',timeout=3)"
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
