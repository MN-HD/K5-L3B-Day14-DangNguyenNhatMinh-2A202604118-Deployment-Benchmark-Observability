# Benchmark & Observability Report — Day 14

**Họ tên** — Dang Nguyen Nhat Minh (2A202604118)
**Ngày chạy** — 27/11/2026
**Môi trường** — Windows, Ubuntu WSL2, Python 3.11 và Docker Desktop.

## 1. SLO của agent

| SLI | Ngưỡng | Lý do |
|---|---:|---|
| p95 latency `/ask` | ≤ 500 ms | Giới hạn độ trễ của phần lớn request và nhạy hơn trung bình với tail latency. |
| Error rate `/ask` | ≤ 2% | Giới hạn phần request không xử lý thành công trong load test local. |
| Accuracy trên golden dataset | ≥ 80% ở baseline, 100% ở bản sửa | Phát hiện suy giảm chất lượng. Bản sửa phải đạt 23/23 và không có regression. |

Ngưỡng cảnh báo của stack Docker là error rate trên 5% trong 1 phút
và p95 trên 1 giây trong 2 phút. Đây là các ngưỡng trong rule Prometheus.

## 2. Benchmark hiệu năng local

### 2.1 Concurrency và latency

Mỗi lần chạy gửi 300 request vào agent v2.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 4,63 | 189,5 | 220,7 | 1.679,4 | 0,00% | PASS |
| 10 | 43,90 | 191,1 | 218,6 | 1.695,9 | 0,67% | PASS |
| 50 | 104,04 | 194,5 | 238,8 | 1.710,2 | 1,33% | PASS |
| 100 | 114,86 | 260,6 | 1.617,4 | 1.799,3 | 1,00% | FAIL p95 |

Từ concurrency 50 lên 100, throughput chỉ tăng từ 104,04 lên
114,86 RPS, trong khi p95 tăng từ 238,8 lên 1.617,4 ms. Tăng số
request đồng thời cho lợi ích throughput giảm dần trong lần chạy này.

### 2.2 Tail latency

Mỗi lần chạy gửi 300 request với concurrency 20 và giữ
`MOCK_ERROR_RATE=0.01`.

| `MOCK_SLOW_RATE` | RPS | Avg (ms) | p95 (ms) | p99 (ms) | Error rate |
|---:|---:|---:|---:|---:|---:|
| 0 | 100,87 | 192,0 | 220,7 | 223,3 | 2,00% |
| 0,03 | 58,62 | 252,3 | 224,4 | 1.707,5 | 1,33% |
| 0,1 | 51,12 | 312,8 | 1.686,3 | 1.711,4 | 1,00% |

p99 phản ánh rõ nhóm request chậm ở mức 3%, khi p95 vẫn gần baseline.
Ở mức 10%, p95 cũng vượt SLO 500 ms dù latency trung bình chỉ 312,8 ms.

## 3. Benchmark chất lượng

| Chỉ số | Agent v1 | Agent v2 | Agent v2 sau khi sửa KB |
|---|---:|---:|---:|
| Accuracy | 4,3% (1/23) | 91,3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 56,9 | 109,3 | 113,6 |
| Tổng cost (USD) | 0,000401 | 0,000764 | 0,000790 |
| Cost / câu đúng (USD) | 0,00040095 | 0,00003639 | 0,00003436 |
| p95 (ms) | 188,9 | 215,0 | 213,5 |
| Quality gate | FAIL | PASS | PASS |

| ID | Keyword bị thiếu | Thay đổi |
|---|---|---|
| `security-02` | token, hết hạn, chữ ký | Thêm tài liệu về JWT và API key, kích hoạt bằng `jwt` hoặc `json web token`. |
| `scaling-03` | cpu, memory, custom metrics | Thêm tài liệu về Kubernetes HPA và các nhóm metric dùng để scale. |

v2 dùng thêm token để đưa ngữ cảnh vào prompt. Tổng cost và p95 tăng so
với v1, nhưng cost trên mỗi câu đúng giảm vì số câu đúng tăng từ 1 lên
21. Sau khi sửa knowledge base, hai câu còn thiếu đều đạt và không có
regression. Tôi đặt `MOCK_ERROR_RATE=0` riêng cho lần eval cuối để kiểm
tra nội dung câu trả lời khi request được xử lý thành công.

Có thể dùng exit code của `run_eval.py` trong một job CI bắt buộc trước
khi merge. Chạy với `--min-accuracy 1.0` và `--baseline` trỏ tới report
đã duyệt. Job thất bại nếu accuracy dưới ngưỡng hoặc có regression.

## 4. Observability stack

### 4.1 Bằng chứng

- [Grafana khi có tải](screenshots/grafana-dashboard.png)
- [Trace chậm trong Jaeger](screenshots/jaeger-slow-trace.png)
- [Trace lỗi trong Jaeger](screenshots/jaeger-error-trace.png)
- [Hai alert firing trong Prometheus](screenshots/prometheus-alert-firing.png)

Ảnh Grafana ghi traffic 39,1 req/s, error rate 1,07% và p95 292,50 ms.
Dashboard cho thấy tình trạng hệ thống và độ trễ. Để phát hiện câu trả
lời sai khi các chỉ số vận hành vẫn tốt, cần chạy eval và theo dõi tín
hiệu chất lượng như phản hồi người dùng hoặc kiểm tra mẫu câu trả lời.

### 4.2 Thí nghiệm lỗi và alert

Tôi chạy A và B đồng thời với 30 Locust users, bắt đầu lúc 13:18:15
giờ Việt Nam. Thời gian bên dưới là mẫu firing đầu tiên từ Prometheus,
với bước truy vấn 5 giây.

| Thí nghiệm | Thay đổi | Alert quan sát | Thời gian | Panel liên quan |
|---|---|---|---:|---|
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 75 giây | Error rate, request theo status |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | 135 giây | p95/p99 latency |
| C | Đổi sang `mock-llm-large` | Chưa chạy riêng | — | Cost USD/giờ |
| D | Pause một instance | Chưa chạy riêng | — | Instances up, Prometheus targets |
| E | Đổi sang v1 | So sánh bằng eval local ở mục 3 | — | Accuracy và regression |

Alert có độ trễ vì Prometheus cần lấy mẫu, đánh giá điều kiện và giữ
điều kiện đúng đủ lâu theo `for`. Vấn đề chất lượng như ở E có thể xảy
ra ngay cả khi hệ thống tiếp tục trả HTTP 200. Có thể phát hiện qua
eval định kỳ, cảnh báo accuracy giảm và kiểm tra mẫu câu trả lời thật.

### 4.3 Debug bằng trace

Trace chậm `47a4ee76be17ae527f93f76a8df93c41` trả `200`. Log đo
tổng thời gian 1.713,5 ms, trong đó `chat mock-llm-small` chiếm
1.687,3 ms, khoảng 98,5%. Jaeger hiển thị retrieval mất 22,5 ms.

```json
{"ts": "2026-11-27T06:21:46.379528+00:00", "level": "INFO", "service": "observable-agent", "instance": "41ff74e61ec6", "event": "llm_call", "trace_id": "47a4ee76be17ae527f93f76a8df93c41", "span_id": "29fd826106298198", "request_id": "6275574a5e96", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 83, "output_tokens": 44, "cost_usd": 3.9e-05, "llm_ms": 1687.3}
```

Trace lỗi `6e880d903dc3407ddd4b04dba3638e17` trả `503`. Jaeger
hiển thị khoảng 855 ms và log `http_request` ghi 853,9 ms. Log
`llm_error` cùng trace ID xác định lỗi đến từ upstream mô phỏng.

```json
{"ts": "2026-11-27T06:21:45.017321+00:00", "level": "INFO", "service": "observable-agent", "instance": "41ff74e61ec6", "event": "llm_error", "trace_id": "6e880d903dc3407ddd4b04dba3638e17", "span_id": "d941b08eafdfa1e3", "request_id": "5f51cd31bb4d", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

## 5. Benchmark scaling với Locust

Mỗi lần chạy dùng 100 users, ramp-up 10 users/giây và thời lượng
2 phút. Bảng dùng dòng `POST /ask` trong từng CSV.

| Số instance được yêu cầu | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---:|---:|---:|---:|---:|---|
| 1 | 60,26 | 190 | 220 | 1.700 | 75 / 7.181 (1,04%) |
| 3 | 59,92 | 190 | 220 | 1.700 | 71 / 7.139 (0,99%) |

Hai lần chạy cho p95 bằng nhau và throughput gần như bằng nhau.
Trace cho thấy mock LLM chiếm phần lớn thời gian ở request chậm.
Số replica trên bảng là giá trị cấu hình yêu cầu trước khi chạy; ảnh
Grafana tại một thời điểm hiển thị 2 instance. Vì vậy, CSV cho thấy
hai lần chạy có kết quả tương tự, nhưng chưa đủ để kết luận 3 replica
thực sự không cải thiện hiệu năng.

## 6. Kết luận

1. Cần xem p95 và p99 cùng throughput để thấy ảnh hưởng của request chậm.
2. Accuracy và cost trên mỗi câu đúng giúp đánh giá hiệu quả của retrieval.
3. Kết hợp metrics, trace và log có cùng `trace_id` giúp tìm bước gây chậm
   hoặc lỗi sau khi alert phát hiện triệu chứng.

Nếu triển khai thật, tôi sẽ thêm synthetic check qua URL công khai,
theo dõi lỗi 5xx ở tầng proxy và cảnh báo khi accuracy giảm trên bộ
eval định kỳ. Tôi sẽ dùng label có số lượng giá trị giới hạn để tránh
tăng quá nhiều time series.

## AI log

Tôi dùng ChatGPT để được hướng dẫn chạy benchmark, bổ sung knowledge
base, sửa đường dẫn package Python trong Dockerfile observability,
đối chiếu log với trace và soạn báo cáo. Tôi tự chạy các phép đo,
kiểm tra output JSON/CSV và lưu các ảnh bằng chứng trên máy của mình.
