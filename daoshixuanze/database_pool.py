import pymssql
import queue

class DatabasePool:
    def __init__(self, min_connections, max_connections, server, user, password, database):
        self.pool = queue.Queue(max_connections)
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.server = server
        self.user = user
        self.password = password
        self.database = database

        # 初始化连接池
        for _ in range(min_connections):
            conn = pymssql.connect(server=self.server, user=self.user, password=self.password, database=self.database)
            self.pool.put(conn)

    def get_connection(self):
        if not self.pool.empty():
            return self.pool.get()
        else:
            # 超过最大连接数时返回None或者创建新连接
            if self.pool.qsize() < self.max_connections:
                conn = pymssql.connect(server=self.server, user=self.user, password=self.password, database=self.database)
                return conn
            else:
                return None  # 如果连接池已满，返回None

    def release_connection(self, conn):
        if conn:
            self.pool.put(conn)

db_pool = DatabasePool(min_connections=5, max_connections=10, server='localhost', user='sa', password='123456', database='graduate_admission_system')
