import pymssql
from database_pool import db_pool  # 引入连接池
from decimal import Decimal

# 使用连接池获取数据库连接
def get_db_connection():
    return db_pool.get_connection()

def get_students_for_tutor(tutor_id):
    conn = get_db_connection()
    if not conn:
        raise Exception("数据库连接不可用")

    cursor = conn.cursor(as_dict=True)
    cursor.execute("""
        SELECT s.student_id, 
               CONVERT(NVARCHAR, s.name) AS name,  
               s.initial_score, 
               s.retest_score, 
               CONVERT(NVARCHAR, sc.admission_status) AS admission_status,  -- 获取录取状态
               sc.tutor_id1, 
               sc.tutor_id2, 
               sc.tutor_id3
        FROM students s
        LEFT JOIN student_choices sc ON s.student_id = sc.student_id
        WHERE (sc.tutor_id1 = %s OR sc.tutor_id2 = %s OR sc.tutor_id3 = %s)
        AND (sc.status != '已拒绝')  -- 排除状态为 '已拒绝' 的学生
    """, (tutor_id, tutor_id, tutor_id))

    students = cursor.fetchall()

    # 为每个学生获取对应的导师姓名和综合成绩
    for student in students:
        student['tutor_names'] = []
        for tutor_id in [student['tutor_id1'], student['tutor_id2'], student['tutor_id3']]:
            tutor_name = get_tutor_name(tutor_id)
            student['tutor_names'].append(tutor_name)

        # 计算综合成绩
        student['comprehensive_score'] = calculate_comprehensive_score(student['initial_score'], student['retest_score'])

    # 按综合成绩排序（降序）
    students = sorted(students, key=lambda x: x['comprehensive_score'], reverse=True)

    db_pool.release_connection(conn)  # 操作完毕后释放连接
    return students

# 在 student_dao.py 或 selection_dao.py 中

def is_first_choice_assigned(student_id, tutor_id):
    """
    检查当前操作的导师是否为该学生的一志愿导师，
    如果是，则允许更新状态
    """
    conn = get_db_connection()  # 获取数据库连接
    cursor = conn.cursor()

    try:
        # 查询学生的第一志愿导师是否为当前操作的导师
        cursor.execute("""
            SELECT student_id
            FROM student_choices
            WHERE student_id = %s AND tutor_id1 = %s
        """, (student_id, tutor_id))

        # 如果查询结果不为空，说明该导师是学生的一志愿导师
        result = cursor.fetchone()

        return result is not None  # 返回是否该导师是学生的一志愿导师
    except Exception as e:
        print(f"Error checking first choice: {e}")
        return False
    finally:
        cursor.close()
        conn.close()



# 获取导师姓名
def get_tutor_name(tutor_id):
    conn = get_db_connection()
    if not conn:
        raise Exception("数据库连接不可用")
    cursor = conn.cursor(as_dict=True)
    cursor.execute("""
        SELECT CONVERT(NVARCHAR, name) AS name
        FROM tutors 
        WHERE tutor_id = %s
    """, (tutor_id,))
    tutor = cursor.fetchone()
    db_pool.release_connection(conn)  # 操作完毕后释放连接
    return tutor['name'] if tutor else "未知导师"


# 计算综合成绩（假设公式为初试成绩 * 0.6 + 复试成绩 * 0.4）
def calculate_comprehensive_score(initial_score, retest_score):
    if initial_score is None or retest_score is None:
        return 0

    # 将Decimal转换为float进行运算，避免类型错误
    initial_score = float(initial_score) if isinstance(initial_score, Decimal) else initial_score
    retest_score = float(retest_score) if isinstance(retest_score, Decimal) else retest_score

    # 计算综合成绩并保留两位小数
    comprehensive_score = initial_score * 0.6 + retest_score * 0.4
    return round(comprehensive_score, 2)
