FROM odoo:18.0

USER root

RUN apt-get update && apt-get install -y \
	ca-certificates \
	tzdata \
	fontconfig \
	fonts-dejavu-core \
	wget \
	xfonts-75dpi \
	xfonts-base \
	&& wget -O /tmp/wkhtmltox.deb https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
	&& apt-get install -y /tmp/wkhtmltox.deb \
	&& pip3 install --no-cache-dir python-docx==1.1.2 \
	&& rm -f /tmp/wkhtmltox.deb \
	&& rm -rf /var/lib/apt/lists/*

RUN rm -rf /usr/lib/python3/dist-packages/odoo/addons

COPY ./addons /usr/lib/python3/dist-packages/odoo/addons
COPY ./odoo/addons /usr/lib/python3/dist-packages/odoo/addons

COPY ./helpdesk /mnt/extra-addons

ENV TZ=Europe/Madrid

USER odoo

RUN echo "list_db = False" >> /etc/odoo/odoo.conf
RUN echo "proxy_mode = True" >> /etc/odoo/odoo.conf
