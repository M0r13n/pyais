FROM python:3.11

LABEL org.opencontainers.image.source github.com/M0r13n/pyais

ENV DISABLE_PIP_VERSION_CHECK=1

# Add a dedicated user
RUN groupadd --gid 1000 pyais
RUN useradd -s /bin/bash -g pyais -u 1000 -m -d /home/pyais pyais
WORKDIR /pyais
RUN chown -R pyais:pyais /pyais
RUN chmod 755 /pyais
USER pyais

COPY . .

RUN pip install -U .
