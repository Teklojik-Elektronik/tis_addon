ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    gcc \
    musl-dev

# Copy requirements
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Copy addon files
COPY run.sh /
COPY web_ui.py /
COPY discovery.py /
COPY const.py /
COPY tis_protocol.py /
COPY templates/ /templates/
COPY static/ /static/

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
