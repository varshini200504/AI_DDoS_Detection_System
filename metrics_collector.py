import time
import psutil
import threading
import json
from datetime import datetime
import numpy as np


class MetricsCollector:
    def __init__(self, output_file='logs/metrics.json'):
        self.output_file = output_file
        self.metrics = {
            'detection_latencies': [],
            'cpu_usage': [],
            'memory_usage': [],
            'flows_per_sec': [],
            'false_positives': 0,
            'false_negatives': 0,
            'true_positives': 0,
            'true_negatives': 0,
        }
        self._stop = False

    def record_detection_latency(self, start_time, end_time):
        latency_ms = (end_time - start_time) * 1000
        self.metrics['detection_latencies'].append(latency_ms)

    def record_system_metrics(self):
        while not self._stop:
            self.metrics['cpu_usage'].append(psutil.cpu_percent(interval=1))
            self.metrics['memory_usage'].append(psutil.virtual_memory().percent)
            time.sleep(0.5)

    def start_background(self):
        t = threading.Thread(target=self.record_system_metrics, daemon=True)
        t.start()

    def stop(self):
        self._stop = True

    def generate_report(self):
        if not self.metrics['detection_latencies']:
            return {}

        report = {
            'timestamp': datetime.now().isoformat(),
            'detection_latency': {
                'mean_ms': float(np.mean(self.metrics['detection_latencies'])),
                'std_ms': float(np.std(self.metrics['detection_latencies'])),
                'min_ms': float(np.min(self.metrics['detection_latencies'])),
                'max_ms': float(np.max(self.metrics['detection_latencies'])),
                'p95_ms': float(np.percentile(self.metrics['detection_latencies'], 95)),
            },
            'cpu_usage': {
                'mean_percent': float(np.mean(self.metrics['cpu_usage'])) if self.metrics['cpu_usage'] else 0,
                'max_percent': float(np.max(self.metrics['cpu_usage'])) if self.metrics['cpu_usage'] else 0,
            },
            'memory_usage': {
                'mean_percent': float(np.mean(self.metrics['memory_usage'])) if self.metrics['memory_usage'] else 0,
                'max_percent': float(np.max(self.metrics['memory_usage'])) if self.metrics['memory_usage'] else 0,
            }
        }
        return report

    def save_report(self):
        report = self.generate_report()
        if not report:
            return
        with open(self.output_file, 'w') as f:
            json.dump(report, f, indent=2)


if __name__ == '__main__':
    mc = MetricsCollector()
    mc.start_background()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mc.stop()
        mc.save_report()
