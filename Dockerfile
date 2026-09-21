FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN set -eux \
    && sed -i \
        -e 's#http://deb.debian.org/#https://deb.debian.org/#g' \
        -e 's#http://security.debian.org/#https://security.debian.org/#g' \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential \
        libjpeg-dev \
        zlib1g-dev \
        libgl1 \
        libegl1 \
        libgles2 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && pip install --default-timeout=1000 -r requirements.txt

COPY . ./

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
