import multiprocessing

bind = "0.0.0.0:7999"

workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
worker_class = "gthread"

timeout = 60

accesslog = "-"
errorlog = "-"
loglevel = "info"

preload_app = True