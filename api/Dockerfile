FROM golang:1.24-alpine AS construcao
WORKDIR /origem
COPY go.* ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -o /servidor ./cmd/servidor

FROM alpine:3.20
RUN apk add --no-cache ca-certificates tzdata
ENV TZ=America/Sao_Paulo
COPY --from=construcao /servidor /servidor
EXPOSE 8080
ENTRYPOINT ["/servidor"]
