FROM golang:1.24.9-alpine3.22 AS build

ENV CGO_ENABLED=0
RUN go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z && \
    go install github.com/minio/mc@RELEASE.2025-08-13T08-35-41Z

FROM alpine:3.22.2

RUN apk add --no-cache ca-certificates curl && \
    addgroup -g 10001 minio && \
    adduser -D -u 10001 -G minio minio && \
    mkdir -p /data && \
    chown minio:minio /data

COPY --from=build /go/bin/minio /usr/local/bin/minio
COPY --from=build /go/bin/mc /usr/local/bin/mc

USER minio
VOLUME ["/data"]
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
