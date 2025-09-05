// JS code placeholder if needed for frontend interactivity
console.log("Script Loaded");
// हे मार्क्स, क्रेडिट आणि अटेंडन्सचा डेटा backend कडून घेईल
// async function fetchStudentData() {
//     const response = await fetch('/student/data?app_id=APP123');
//     const data = await response.json();

//     renderMarksChart(data.marks);
//     renderCreditChart(data.credits);
//     renderAttendanceChart(data.attendance);
// }
async function fetchStudentData() {
    const response = await fetch(`/student/data?app_id=${app_id}`);
    const data = await response.json();

    if (data.status === "success") {
        // उदाहरणार्थ: मार्क्स आणि क्रेडिट display करणे
        displayMarks(data.marks);
        displayCredits(data.credits);
        drawMarksGraph(data.marks);
        drawAttendanceGraph(data.attendance);
    } else {
        alert("डेटा लोड करण्यात अडचण आली!");
    }
}

function renderMarksChart(marks) {
    const ctx = document.getElementById('marksChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: marks.map(m => m.month),
            datasets: [{
                label: 'Marks',
                data: marks.map(m => m.obtained),
                backgroundColor: 'rgba(54, 162, 235, 0.6)'
            }]
        }
    });
}

function renderCreditChart(credits) {
    const ctx = document.getElementById('creditChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: credits.map(c => c.month),
            datasets: [{
                label: 'Credit Score',
                data: credits.map(c => c.score),
                borderColor: 'green',
                fill: false
            }]
        }
    });
}

function renderAttendanceChart(attendance) {
    const ctx = document.getElementById('attendanceChart').getContext('2d');
    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ['Present', 'Absent'],
            datasets: [{
                data: [attendance.present, attendance.absent],
                backgroundColor: ['#4caf50', '#f44336']
            }]
        }
    });
}

fetchStudentData();
