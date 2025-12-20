#!/bin/bash

set -e

if [ ! -f .env ]; then
    echo ".env 파일이 없습니다. .env 파일을 생성하고 TERRAFORM_SIDECAR_METALLB_IP를 설정하세요."
    exit 1
fi

source .env

if [ -z "$TERRAFORM_SIDECAR_METALLB_IP" ]; then
    echo "TERRAFORM_SIDECAR_METALLB_IP가 .env 파일에 설정되지 않았습니다."
    exit 1
fi

export TERRAFORM_SIDECAR_METALLB_IP

echo "이미지 빌드 및 푸시 중..."
./deploy/push-image.sh terraform-sidecar latest

echo "기존 리소스 삭제 중..."
kubectl delete -f deploy/service.yaml --ignore-not-found=true
kubectl delete -f deploy/deployment.yaml --ignore-not-found=true
kubectl delete -f deploy/pvc.yaml --ignore-not-found=true
kubectl delete -f deploy/pv.yaml --ignore-not-found=true

echo "리소스 생성 중..."
kubectl apply -f deploy/pv.yaml
kubectl apply -f deploy/pvc.yaml
envsubst '${TERRAFORM_SIDECAR_METALLB_IP}' < deploy/service.yaml | kubectl apply -f -
kubectl apply -f deploy/deployment.yaml

echo "완료"

