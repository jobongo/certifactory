FROM nginx:alpine

RUN apk add --no-cache openssl

COPY nginx.conf.template /etc/nginx/templates/nginx.conf.template
COPY entrypoint.sh /entrypoint.sh

RUN rm -f /etc/nginx/conf.d/default.conf

EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
