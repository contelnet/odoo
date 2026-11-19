FROM odoo:18.0

USER root

RUN for f in /etc/apt/sources.list /etc/apt/sources.list.d/*; do \
        [ -f "$f" ] && sed -i 's|http://archive.ubuntu.com/ubuntu|http://azure.archive.ubuntu.com/ubuntu|g' "$f"; \
    done \
    && apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 update \
    && apt-get -o Acquire::Retries=5 -o Acquire::http::Timeout=30 install -y --no-install-recommends --fix-missing \
        python3-docx \
        fontconfig \
        fonts-dejavu-core \
        fonts-freefont-ttf \
        fonts-liberation2 \
        fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

RUN wkhtmltopdf --version | grep -q 'with patched qt'
    

RUN rm -rf /usr/lib/python3/dist-packages/odoo/addons

COPY ./addons /usr/lib/python3/dist-packages/odoo/addons
COPY ./odoo/addons /usr/lib/python3/dist-packages/odoo/addons

COPY ./helpdesk /mnt/extra-addons

ENV TZ=Europe/Madrid

RUN echo "list_db = False" >> /etc/odoo/odoo.conf
RUN echo "proxy_mode = True" >> /etc/odoo/odoo.conf

USER odoo
