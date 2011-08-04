# -*- coding: utf-8 -*-

import redis, datetime
from hotqueue import key_for_name


class RedisMonitor(object):

    def __init__(self, servers, hotqueues=None):
        self.servers = servers
        self.hotqueues = hotqueues

    def getStats(self, jsonOutput = None):
        response = []
        for server in self.servers:
            response.append(self.getStatsPerServer(server, self.hotqueues))

        if jsonOutput:
            new_response = []
            for item in response:
                for key, value in item.items():
                    new_key = item.get("addr") + "_" + key
                    new_response.append({new_key: value})

            return new_response

        return response

    def getStatsPerServer(self, server, hotqueues):

        try:
            connection = redis.Redis(host=server[0], port=server[1], db=0)
            info       =  connection.info()
            info.update({
                "server_name"        : server,
                "status"             : "up",
                "last_save_humanized": datetime.datetime.fromtimestamp(info.get("last_save_time"))
            })

            connection.connection_pool.disconnect()
            if hotqueues:
                for hotqueue in hotqueues:
                    if hotqueue[0] == server:
                        store = redis.Redis(host=server[0], port=server[1], db=hotqueue[1])
                        # code graciously cribbed from https://github.com/richardhenry/hotwatch
                        def length_for_names(store, *queue_names):
                            for queue_name in queue_names:
                                yield queue_name, store.llen(key_for_name(queue_name))

                        hotqueue_info = {}
                        for item in length_for_names(store, *hotqueue[2]):
                            name, length = item
                            hotqueue_info.update({name: length})
                        store.connection_pool.disconnect()
                        info.update({'hotqueues': hotqueue_info})

        except redis.exceptions.ConnectionError:
            info =  {
                "status"            : "down",
                "server_name"       : server,
                "connected_clients" : 0,
                "used_memory_human" : '?',
            }

        info.update({
            "addr"             : info.get("server_name")[0].replace(".", "-") +  str(info.get("server_name")[1]),
        })

        screen_strategy = 'normal'
        if info.get("status") == 'down':
            screen_strategy = 'hidden'

        info.update({
            "screen_strategy": screen_strategy,
        })

        return info
