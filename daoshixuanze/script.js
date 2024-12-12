// AJAX 获取学生列表
function fetchStudents() {
    fetch('/api/get_students')
        .then(response => response.json())
        .then(data => {
            const studentTableBody = document.getElementById('student-table-body');
            studentTableBody.innerHTML = '';  // 清空表格内容

            data.forEach(student => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${student.student_id}</td>
                    <td>${student.name}</td>
                    <td>${student.gender}</td>
                    <td>${student.major}</td>
                    <td>${student.initial_score}</td>
                    <td>${student.retest_score}</td>
                    <td>${student.application_status}</td>
                    <td>${student.admission_status}</td>
                    <td>
                        <button onclick="updateAdmissionStatus(${student.student_id}, '录取')">录取</button>
                        <button onclick="updateAdmissionStatus(${student.student_id}, '拒绝')">拒绝</button>
                    </td>
                `;
                studentTableBody.appendChild(row);
            });
        });
}

// AJAX 更新学生录取状态
function updateAdmissionStatus(studentId, status) {
    fetch(`/api/update_admission_status/${studentId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status: status })
    })
    .then(response => response.json())
    .then(data => {
        alert(`学生 ${studentId} 的录取状态更新为 ${status}`);
        fetchStudents();  // 更新表格
    });
}

// 页面加载时获取学生数据
document.addEventListener('DOMContentLoaded', fetchStudents);
