import pymssql
from database_pool import db_pool

# 使用连接池获取连接
def get_db_connection():
    return db_pool.get_connection()

# 登录验证
def validate_tutor(tutor_id, password):
    conn = get_db_connection()
    if not conn:
        raise Exception("数据库连接不可用")

    cursor = conn.cursor(as_dict=True)
    cursor.execute("""
        SELECT tutor_id, CONVERT(NVARCHAR, name) AS name, has_qualification
        FROM tutors
        WHERE tutor_id = %s AND secret = %s
    """, (tutor_id, password))
    tutor = cursor.fetchone()
    db_pool.release_connection(conn)  # 操作完毕后释放连接

    return tutor
