import logging
import logging.handlers
import os
import sys
import opentracing
import time
import copy
import json
from bb_logger.bb_handler.save_file_handler import SafeFileHandler

folder = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ''))
sys.path.append(folder)


class Logger:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super().__new__(cls)
            cls()._init_logger(**kwargs)
        return cls._instance

    def _init_logger(self, **kwargs):
        path = kwargs['path'] if 'path' in kwargs else './'
        if not os.path.exists(path):
            os.mkdir(path)
        name = kwargs['name'] if 'name' in kwargs else 'default'
        self._name = name
        file = path + '/' + name

        service = kwargs['service'] if 'service' in kwargs else True
        trace = kwargs['trace'] if 'trace' in kwargs else False
        audit = kwargs['audit'] if 'audit' in kwargs else False
        format = kwargs['format'] if 'format' in kwargs else '%(asctime)s - %(levelname)s - ' + name + ': %(message)s'
        level = kwargs['level'] if 'level' in kwargs else logging.INFO
        backupCount = kwargs['backupCount'] if 'backupCount' in kwargs else 0

        if service is True:
            self._create_logger('service', file + '.log', level, format, backupCount)
        if trace is True:
            self._create_logger('trace', file + '.trace.log', level, format, backupCount)
        if audit is True:
            self._create_logger('audit', file + '.audit.log', level, format, backupCount)
        return

    def _create_logger(self, type, file, level, format, backupCount):
        if type == 'service':
            self._service = logging.getLogger(type)
        elif type == 'trace':
            self._trace = logging.getLogger(type)
        elif type == 'audit':
            self._audit = logging.getLogger(type)

        logger_format = format
        if type == 'audit':
            logger_format = '%(message)s'

        handler = SafeFileHandler(file, backupCount=backupCount, encoding='utf8')
        formatter = logging.Formatter(logger_format)
        handler.setFormatter(formatter)
        self.addHandler(type, handler)
        self.setLevel(type, level)

    def _print_log(self, func, message):
        func(message)
        return

    def _get_ot(self, span=None, ls_tracer=None):
        ot = {}
        if span and ls_tracer:
            span.finish()
            ls_tracer.inject(span.context, opentracing.Format.TEXT_MAP, ot)

            ot_info = {
                'ot-traceid': ot['ot-tracer-traceid'],
                'ot-spanid': ot['ot-tracer-spanid'],
                'ot-parent-spanid':  str(hex(span.parent_id))[2:] if span.parent_id is not None else '',
                'ot-starttime': span.start_time,
                'ot-duration': span.duration,
            }
            return ot_info
        else:
            return None

    @classmethod
    def addHandler(cls, name, handler):
        if name == 'service':
            cls()._service.addHandler(handler)
        elif name == 'trace':
            cls()._trace.addHandler(handler)
        elif name == 'audit':
            cls()._audit.addHandler(handler)

    @classmethod
    def setLevel(cls, name, level):
        if name == 'service':
            cls()._service.setLevel(level)
        elif name == 'trace':
            cls()._trace.setLevel(level)
        elif name == 'audit':
            cls()._audit.setLevel(level)

    @classmethod
    def service(cls, message, level='info'):
        func_map = {
            'info': cls()._service.info,
            'warning': cls()._service.warning,
            'debug': cls()._service.debug,
            'error': cls()._service.error,
            'exception': cls()._service.exception,
            'critical': cls()._service.critical
        }
        cls()._print_log(func_map[level], message)
        return

    @classmethod
    def trace(cls, message, span=None, ls_tracer=None, level='info'):
        ot = cls()._get_ot(span, ls_tracer)
        ot_info = ''
        if ot:
            ot_info = 'ot-traceid:%s ot-parent-spanid:%s ot-spanid:%s ot-starttime:%s ot-duration:%s ' \
                            %(ot['ot-traceid'],
                            ot['ot-parent-spanid'],
                            ot['ot-spanid'],
                            ot['ot-starttime'],
                            ot['ot-duration'])
        else:
            ot_info = 'span or ls_tracer is wrong!! Please check it.'

        func_map = {
            'info': cls()._trace.info,
            'warning': cls()._trace.warning,
            'debug': cls()._trace.debug,
            'error': cls()._trace.error,
            'exception': cls()._trace.exception,
            'critical': cls()._trace.critical
        }
        traceMessage = ot_info + ' ' + message
        cls()._print_log(func_map[level], traceMessage)
        return

    @classmethod
    def audit(cls, audit_info, level='info'):
        func_map = {
            'info': cls()._audit.info,
            'warning': cls()._audit.warning,
            'debug': cls()._audit.debug,
            'error': cls()._audit.error,
            'exception': cls()._audit.exception,
            'critical': cls()._audit.critical
        }
        # audit log format (dict type)
        dicts = copy.deepcopy(audit_info)
        dicts['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        dicts['service'] = cls()._name
        message = json.dumps(dicts, ensure_ascii=False)
        cls()._print_log(func_map[level], message)
        return


def main():
    # example
    format = '%(asctime)s %(levelname)s demo: %(message)s'  # for service log, audit and tracing 为内部强制格式
    name = 'demo'
    path = './logs'
    backupCount = 1

    ot = {
        'ot-traceid': '12345678',
        'ot-spanid': '11111111',
        'ot-parent-spanid':  '22222222',
        'ot-starttime': '1234',
        'ot-duration': '5678',
    }

    """
        path: 日志目录， default: 当前目录
        name: app name, default: default
        service:  启用日常日志，defalut: True
        trace: 启用trace日志, default: False
        format: 日志格式化，默认格式 '%(asctime)s %(levelname)s name %(message)s' 
            ex: 2018-04-23 11:42:45,468 INFO demoApp: test bb logger
        level: logging level  default: info
    """
    args = {
        'path': path,
        'name': name,
        'service': True,
        'trace': True,
        'audit': True,
        'format': format,
        'level': logging.INFO
    }
    Logger(**args)
    Logger.service('test bb logger', 'info')
    Logger.trace('trace bb logger')
    Logger.audit(dict(content='测试'))


if __name__ == '__main__':
    main()
