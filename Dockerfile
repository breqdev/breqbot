# First stage: install requirements, build application
FROM python:3.8 AS builder
COPY requirements.txt .
RUN pip install --user --no-warn-script-location -r requirements.txt

# Second stage: copy only files needed for final application
FROM python:3.8-slim
WORKDIR /code
COPY --from=builder /root/.local /root/.local
COPY ./src .

ENV PATH=/root/.local:$PATH
CMD [ "python", "./breqbot.py" ]
