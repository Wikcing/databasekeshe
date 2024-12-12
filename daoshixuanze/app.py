from flask import Flask, render_template, request, redirect, url_for, flash
import tutor_dao
import student_dao
from selection_dao import get_students_for_tutor, get_tutor_name,is_first_choice_assigned
from database_pool import db_pool  # 确保导入了数据库池
from student_dao import get_students_selected_by_tutor,get_unassigned_students
import os
import random

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 使用随机密钥作为 secret_key

def get_db_connection():
    return db_pool.get_connection()
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        tutor_id = request.form['tutor_id']
        password = request.form['password']

        # 使用 tutor_dao 中的验证方法，获取导师信息和资格
        tutor = tutor_dao.validate_tutor(tutor_id, password)

        # 判断导师是否存在，以及是否有资格
        if tutor:
            if tutor['has_qualification']:  # 检查导师是否有资格
                return redirect(url_for('choose_function', tutor_id=tutor['tutor_id'], tutor_name=tutor['name']))
            else:
                return render_template('login.html', message="该导师没有招生资格")
        else:
            return render_template('login.html', message="账号或密码错误")

    return render_template('login.html')

@app.route('/choose_function')
def choose_function():
    tutor_id = request.args.get('tutor_id')
    tutor_name = request.args.get('tutor_name')

    if not tutor_id or not tutor_name:
        return "错误：未能获取导师信息！", 400

    return render_template('choose_function.html', tutor_id=tutor_id, tutor_name=tutor_name)


@app.route('/students_list', methods=['GET'])
def students_list():
    tutor_id = request.args.get('tutor_id')  # 获取 URL 参数中的 tutor_id
    status = request.args.get('status')  # 获取 URL 参数中的 status（筛选条件）

    # 根据 status 是否存在，选择不同的查询方法
    if status:
        students = student_dao.get_students_by_status(status)  # 按照 status 筛选学生
    else:
        students = student_dao.get_students()  # 显示所有学生

    # 渲染学生列表页面，并传递 tutor_id 和学生列表
    return render_template('students_list.html', students=students, tutor_id=tutor_id, status=status)

@app.route('/assign_students', methods=['GET', 'POST'])
def assign_students():
    tutor_id = request.args.get('tutor_id')  # 获取 tutor_id 参数
    tutor_name = request.args.get('tutor_name')  # 获取 tutor_name 参数

    if not tutor_id:
        return "错误：未能获取导师信息！", 400

    # 获取导师的学生列表
    tutor_name = get_tutor_name(tutor_id)
    students = get_students_for_tutor(tutor_id)

    if request.method == 'POST':
        selected_students = request.form.getlist('selected_students')  # 获取选择的学生

        for student_id in selected_students:
            update_student_status(student_id, tutor_id, '已分配')  # 更新学生状态

        return redirect(url_for('choose_function', tutor_id=tutor_id))  # 重定向到选择功能页面

    return render_template('assign_students.html', tutor_id=tutor_id, tutor_name=tutor_name, students=students)  # 渲染分配学生页面



@app.route('/update_status', methods=['POST'])
def update_status():
    student_id = request.form['student_id']  # 获取学生ID
    tutor_id = request.form['tutor_id']  # 获取导师ID
    new_status = request.form['new_status']  # 获取新的状态

    # 判断是否是该学生的一志愿导师，且该学生的状态可以由当前导师更新
    if not is_first_choice_assigned(student_id, tutor_id):
        flash("只有该学生的一志愿导师才能优先更新状态！", "danger")
        return redirect(url_for('assign_students', tutor_id=tutor_id))  # 跳回学生选择页面

    # 如果状态为空，给出提示
    if not new_status:
        flash("请选择一个有效的状态！", "danger")
        return redirect(url_for('assign_students', tutor_id=tutor_id))

    # 判断状态并更新
    if new_status == 'assigned':  # 如果选择的是 "已分配"
        # 获取数据库连接
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 获取导师已分配的学生数和最大学生数
            cursor.execute("""
                SELECT admitted_students_count, max_student_count 
                FROM tutors 
                WHERE tutor_id = %s
            """, (tutor_id,))
            result = cursor.fetchone()

            if result:
                admitted_students_count, max_students_count = result
                # 判断导师是否已达最大学生数
                if admitted_students_count >= max_students_count:
                    # 如果已分配学生数 >= 最大学生数，提示并不执行更新
                    flash(f"导师已达最大学生数 ({max_students_count} 人)，无法分配更多学生！", "danger")
                    return redirect(url_for('assign_students', tutor_id=tutor_id))

            # 更新学生选择表中的状态
            cursor.execute("""
                UPDATE student_choices 
                SET admission_status = %s, selected_by_tutor = %s
                WHERE student_id = %s 
            """, ('已分配', tutor_id, student_id))

            # 同步更新导师表中的已录取学生数量
            cursor.execute("""
                UPDATE tutors
                SET admitted_students_count = admitted_students_count + 1
                WHERE tutor_id = %s
            """, (tutor_id,))

            conn.commit()  # 提交更改
            flash("学生状态更新成功！", "success")

        except Exception as e:
            conn.rollback()  # 如果出错，回滚事务
            flash(f"更新失败: {str(e)}", "danger")
        finally:
            conn.close()  # 关闭数据库连接

    elif new_status == 'accepted':
        flash("学生状态已经是‘已分配’，无需再次更新为‘已分配’！", "warning")

    else:
        flash("无效的状态选择！", "danger")

    return redirect(url_for('assign_students', tutor_id=tutor_id))  # 跳回学生选择页面

@app.route('/update_status2', methods=['POST'])
def update_status2():
    student_id = request.form['student_id']  # 获取学生ID
    tutor_id = request.form['tutor_id']  # 获取导师ID
    new_status = request.form['new_status']  # 获取新的状态

    # 如果状态为空，给出提示
    if not new_status:
        flash("请选择一个有效的状态！", "danger")
        return redirect(url_for('unassigned_students', tutor_id=tutor_id))

    # 获取数据库连接
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT tutor_id
            FROM tutors
            WHERE admitted_students_count = 0 AND has_qualification = 1
        """)
        unassigned_tutors = cursor.fetchall()

        # 如果存在未分配学生的导师
        if unassigned_tutors:
            # 检查当前操作的导师是否有学生
            cursor.execute("""
                SELECT admitted_students_count
                FROM tutors
                WHERE tutor_id = %s
            """, (tutor_id,))
            result = cursor.fetchone()

            if result and result[0] > 0:  # 当前导师已分配学生
                flash("当前有未分配学生的导师，不能更改该导师的状态！", "warning")
                return redirect(url_for('unassigned_students', tutor_id=tutor_id))

        # 判断状态并更新
        if new_status == 'assigned':  # 如果选择的是 "已分配"
            # 获取导师已分配的学生数和最大学生数
            cursor.execute("""
                SELECT admitted_students_count, max_student_count
                FROM tutors
                WHERE tutor_id = %s
            """, (tutor_id,))
            result = cursor.fetchone()

            if result:
                admitted_students_count, max_students_count = result
                # 判断导师是否已达最大学生数
                if admitted_students_count >= max_students_count:
                    # 如果已分配学生数 >= 最大学生数，提示并不执行更新
                    flash(f"导师已达最大学生数 ({max_students_count} 人)，无法分配更多学生！", "danger")
                    return redirect(url_for('unassigned_students', tutor_id=tutor_id))

            # 更新学生选择表中的状态
            cursor.execute("""
                UPDATE student_choices
                SET admission_status = %s, selected_by_tutor = %s
                WHERE student_id = %s
            """, ('已分配', tutor_id, student_id))

            # 同步更新导师表中的已录取学生数量
            cursor.execute("""
                UPDATE tutors
                SET admitted_students_count = admitted_students_count + 1
                WHERE tutor_id = %s
            """, (tutor_id,))

            conn.commit()  # 提交更改
            flash("学生状态更新成功！", "success")

        elif new_status == 'accepted':
            flash("学生状态已经是‘已分配’，无需再次更新为‘已分配’！", "warning")

        else:
            flash("无效的状态选择！", "danger")

    except Exception as e:
        conn.rollback()  # 如果出错，回滚事务
        flash(f"更新失败: {str(e)}", "danger")
    finally:
        conn.close()  # 关闭数据库连接

    return redirect(url_for('unassigned_students', tutor_id=tutor_id))  # 跳回学生选择页面

@app.route('/update_status3', methods=['POST'])
def update_status3():
    tutor_id = request.form['tutor_id']  # 获取导师ID

    # 获取数据库连接
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 查询未分配导师
        cursor.execute("""
            SELECT tutor_id
            FROM tutors
            WHERE admitted_students_count = 0 AND has_qualification = 1
        """)
        unassigned_tutors = cursor.fetchall()

        # 如果有未分配导师，检查当前操作的导师是否已分配学生
        if unassigned_tutors:
            cursor.execute("""
                SELECT admitted_students_count
                FROM tutors
                WHERE tutor_id = %s
            """, (tutor_id,))
            result = cursor.fetchone()

            if result and result[0] > 0:  # 当前导师已分配学生
                flash("当前有未分配学生的导师，不能更改该导师的状态！", "warning")
                return redirect(url_for('random_assign_student', tutor_id=tutor_id))

        # 检查导师是否已达到最大学生数
        cursor.execute("""
            SELECT admitted_students_count, max_student_count
            FROM tutors
            WHERE tutor_id = %s
        """, (tutor_id,))
        result = cursor.fetchone()

        if result:
            admitted_students_count, max_students_count = result
            # 判断导师是否已达最大学生数
            if admitted_students_count >= max_students_count:
                flash(f"导师已达最大学生数 ({max_students_count} 人)，无法分配更多学生！", "danger")
                return redirect(url_for('random_assign_student', tutor_id=tutor_id))
        else:
            flash("无法获取导师信息，请重试！", "danger")
            return redirect(url_for('random_assign_student', tutor_id=tutor_id))

        # 查询所有未分配的学生
        unassigned_students = get_unassigned_students()

        if not unassigned_students:
            flash("当前没有未分配的学生！", "info")
            return redirect(url_for('random_assign_student', tutor_id=tutor_id))

        # 随机选择一个未分配的学生
        random_student = random.choice(unassigned_students)
        student_id = random_student['student_id']  # 获取学生ID

        # 更新学生选择表中的状态
        cursor.execute("""
            UPDATE student_choices
            SET admission_status = %s, selected_by_tutor = %s
            WHERE student_id = %s
        """, ('已分配', tutor_id, student_id))

        # 同步更新导师表中的已录取学生数量
        cursor.execute("""
            UPDATE tutors
            SET admitted_students_count = admitted_students_count + 1
            WHERE tutor_id = %s
        """, (tutor_id,))

        conn.commit()  # 提交更改
        flash("学生随机分配成功！", "success")

    except Exception as e:
        conn.rollback()  # 如果出错，回滚事务
        flash(f"更新失败: {str(e)}", "danger")
    finally:
        conn.close()  # 关闭数据库连接

    return redirect(url_for('random_assign_student', tutor_id=tutor_id))  # 跳回学生选择页面

@app.route('/unassigned_students', methods=['GET'])
def unassigned_students():
    tutor_id = request.args.get('tutor_id')  # 获取 tutor_id 参数

    if not tutor_id:
        return "错误：未能获取导师信息！", 400  # 如果没有 tutor_id，返回错误信息

    students = get_unassigned_students()

    # 如果没有未分配的学生，给出提示
    if not students:
        flash("当前没有未分配的学生！", "info")

    # 渲染 unassigned_students.html 页面，并传递学生数据和导师ID
    return render_template('unassigned_students.html', students=students, tutor_id=tutor_id)
@app.route('/assigned_students')
def assigned_students():
    tutor_id = request.args.get('tutor_id')

    if not tutor_id:
        return "导师ID是必需的", 400

    try:
        students = get_students_selected_by_tutor(tutor_id)

        return render_template('assigned_students.html', students=students)

    except Exception as e:
        return f"出现错误：{e}", 500  # 如果发生错误，返回错误信息
@app.route('/random_assign_student', methods=['GET'])
def random_assign_student():
    tutor_id = request.args.get('tutor_id')  # 获取 tutor_id 参数

    if not tutor_id:
        return "错误：未能获取导师信息！", 400  # 如果没有 tutor_id，返回错误信息

    students = get_unassigned_students()

    # 如果没有未分配的学生，给出提示
    if not students:
        flash("当前没有未分配的学生！", "info")

    return render_template('random_assign_student.html', students=students, tutor_id=tutor_id)
if __name__ == '__main__':
    app.run(debug=True)
