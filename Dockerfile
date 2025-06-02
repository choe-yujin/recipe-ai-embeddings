# opensearch 기본 이미지에서 시작
FROM opensearchproject/opensearch:2.4.0

# nori 플러그인 설치
RUN /usr/share/opensearch/bin/opensearch-plugin install --batch analysis-nori

