ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python, jq and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    jq \
    bash

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY web_ui.py .
COPY discovery.py .
COPY const.py .
COPY tis_protocol.py .
COPY run.sh /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
