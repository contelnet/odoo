FROM odoo:18.0

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        wkhtmltopdf \
        python3-docx \
    && rm -rf /var/lib/apt/lists/*
    

RUN rm -rf /usr/lib/python3/dist-packages/odoo/addons

COPY ./addons /usr/lib/python3/dist-packages/odoo/addons
COPY ./odoo/addons /usr/lib/python3/dist-packages/odoo/addons

COPY ./helpdesk /mnt/extra-addons

ENV TZ=Europe/Madrid

RUN echo "list_db = False" >> /etc/odoo/odoo.conf
RUN echo "proxy_mode = True" >> /etc/odoo/odoo.conf

USER odoo
