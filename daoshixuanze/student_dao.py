import pymssql
from database_pool import db_pool

# 使用连接池获取连接
def get_db_connection():
    return db_pool.get_connection()

# 获取学生列表
def get_students():
    conn = get_db_connection()
    if not conn:
        raise Exception("数据库连接不可用")

    cursor = conn.cursor(as_dict=True)
    cursor.execute("""
        SELECT s.student_id, 
               CONVERT(NVARCHAR, s.name) AS name,  
               CONVERT(NVARCHAR, s.gender) AS gender,  
               CONVERT(NVARCHAR, s.undergrad_info) AS undergrad_info,  
               s.initial_score, 
               s.retest_score, 
               s.major_id, 
               CONVERT(NVARCHAR, sc.status) AS status,  
               CONVERT(NVARCHAR, sc.admission_status) AS admission_status,  
               CONVERT(NVARCHAR, t1.name) AS tutor_name_1,  
               CONVERT(NVARCHAR, t2.name) AS tutor_name_2,  
               CONVERT(NVARCHAR, t3.name) AS tutor_name_3
        FROM students s
        LEFT JOIN student_choices sc ON s.student_id = sc.student_id
        LEFT JOIN tutors t1 ON sc.tutor_id1 = t1.tutor_id
        LEFT JOIN tutors t2 ON sc.tutor_id2 = t2.tutor_id
        LEFT JOIN tutors t3 ON sc.tutor_id3 = t3.tutor_id
    """)
    students = cursor.fetchall()
    db_pool.release_connection(conn)  # 操作完毕后释放连接
    return students
def get_students_by_status(status):
    conn = get_db_connection()
    if not conn:
        raise Exception("数据库连接不可用")

    cursor = conn.cursor(as_dict=True)
    cursor.execute("""
        SELECT s.student_id, 
               CONVERT(NVARCHAR, s.name) AS name,  
               CONVERT(NVARCHAR, s.gender) AS gender,  
               CONVERT(NVARCHAR, s.undergrad_info) AS undergrad_info,  
               s.initial_score, 
               s.retest_score, 
               s.major_id, 
               CONVERT(NVARCHAR, sc.status) AS status,  
               CONVERT(NVARCHAR, sc.admission_status) AS admission_status,  
               CONVERT(NVARCHAR, t1.name) AS tutor_name_1,  
               CONVERT(NVARCHAR, t2.name) AS tutor_name_2,  
               CONVERT(NVARCHAR, t3.name) AS tutor_name_3
        FROM students s
        LEFT JOIN student_choices sc ON s.student_id = sc.student_id
        LEFT JOIN tutors t1 ON sc.tutor_id1 = t1.tutor_id
        LEFT JOIN tutors t2 ON sc.tutor_id2 = t2.tutor_id
        LEFT JOIN tutors t3 ON sc.tutor_id3 = t3.tutor_id
        WHERE sc.status = %s
    """, (status,))
    students = cursor.fetchall()
    db_pool.release_connection(conn)
    return students
def get_students_selected_by_tutor(tutor_id):
    conn = get_db_connection()  # 获取数据库连接
    if not conn:
        raise Exception("数据库连接不可用")

    cursor = conn.cursor(as_dict=True)

    # 查询已分配给当前导师的学生（包括学生的基本信息、录取状态和导师选择状态）
    query = """
        SELECT s.student_id, 
               CONVERT(NVARCHAR, s.name) AS name,  
               CONVERT(NVARCHAR, s.gender) AS gender,  
               CONVERT(NVARCHAR, s.undergrad_info) AS undergrad_info,  
               s.initial_score, 
               s.retest_score, 
               CONVERT(NVARCHAR, sc.admission_status) AS admission_status,  
               -- 显示学生是否由当前导师选择
               CASE 
                   WHEN sc.selected_by_tutor = %s THEN '已选择'
                   ELSE '未选择'
               END AS selected_by_tutor
        FROM students s
        LEFT JOIN student_choices sc ON s.student_id = sc.student_id
        WHERE sc.admission_status = '已分配'
        AND sc.selected_by_tutor = %s
    """

    # 执行查询
    cursor.execute(query, (tutor_id, tutor_id))
    students = cursor.fetchall()

    db_pool.release_connection(conn)  # 操作完毕后释放连接

    return students
def get_unassigned_students():
    """
    获取状态为‘已通过’且‘admission_status’为‘未分配’的学生，包含学生编号、姓名、性别、初试成绩、复试成绩、学科信息和学生状态。
    """
    conn = get_db_connection()  # 获取数据库连接
    if not conn:
        raise Exception("数据库连接不可用")

    cursor = conn.cursor(as_dict=True)
    try:
        # 查询状态为‘已通过’且‘admission_status’为‘未分配’的学生
        query = """
            SELECT 
                s.student_id, 
                CONVERT(NVARCHAR, s.name) AS name,  
                CONVERT(NVARCHAR, s.gender) AS gender,  
                CONVERT(NVARCHAR, s.undergrad_info) AS undergrad_info,  
                s.initial_score, 
                s.retest_score, 
                s.major_id, 
                CONVERT(NVARCHAR, sc.status) AS status,  
                CONVERT(NVARCHAR, sc.admission_status) AS admission_status
            FROM students s
            LEFT JOIN student_choices sc ON s.student_id = sc.student_id
            LEFT JOIN tutors t1 ON sc.tutor_id1 = t1.tutor_id
            LEFT JOIN tutors t2 ON sc.tutor_id2 = t2.tutor_id
            LEFT JOIN tutors t3 ON sc.tutor_id3 = t3.tutor_id
            WHERE sc.status = '已通过' AND sc.admission_status = '未分配'
        """
        cursor.execute(query)
        students = cursor.fetchall()

        return students

    except Exception as e:
        print(f"获取未分配学生失败: {str(e)}")
        return []
    finally:
        cursor.close()
        conn.close()  # 关闭数据库连接


# 更新学生的录取状态
def update_admission_status(student_id, new_status):
    conn = get_db_connection()
    if not conn:
        raise Exception("数据库连接不可用")

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE student_choices 
        SET admission_status = %s 
        WHERE student_id = %s
    """, (new_status, student_id))
    conn.commit()
    db_pool.release_connection(conn)  # 操作完毕后释放连接
