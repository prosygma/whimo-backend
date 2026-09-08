from multiprocessing import cpu_count

bind = "0.0.0.0:8000"
workers = cpu_count() + 1
worker_class = "gthread"
threads = 4
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
