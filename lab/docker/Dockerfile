FROM --platform=linux/amd64 php:8.4.26-apache

RUN mkdir -p /tmp/sess && chmod 777 /tmp/sess

COPY zz-lab.ini /usr/local/etc/php/conf.d/zz-lab.ini
COPY index.php  /var/www/html/index.php
