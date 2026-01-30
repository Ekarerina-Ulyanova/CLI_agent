FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN git config --global user.name "Coding Agent" && \
    git config --global user.email "agent@example.com"

RUN useradd -m -u 1000 agent && chown -R agent:agent /app
USER agent

CMD ["python", "main.py", "run"]