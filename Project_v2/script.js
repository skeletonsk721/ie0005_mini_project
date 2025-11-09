

document.getElementById('predictionForm').addEventListener('submit', function(e) {
    e.preventDefault();

    // Get form data
    const birthday = document.getElementById('birthday').value;
    const gender = document.getElementById('gender').value;
    const height = document.getElementById('height').value;
    const weight = document.getElementById('weight').value;
    const systolic = document.getElementById('systolic').value;
    const diastolic = document.getElementById('diastolic').value;
    const cholesterol = document.getElementById('cholesterol').value;
    const glucose = document.getElementById('glucose').value;
    // New fields
    const smoking = document.getElementById('smoking').value;
    const alcohol = document.getElementById('alcohol').value;
    const physical = document.getElementById('physical').value;

    // Simple validation
    if (!birthday || !gender || !height || !weight || !systolic || !diastolic ||
        !cholesterol || !glucose || !smoking || !alcohol || !physical) {
        alert('Please fill in all fields');
        return;
    }

    // Show loading state
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing data...';
    resultDiv.classList.remove('highlight');

    // Build payload for backend
    const payload = {
        birthday: birthday,
        gender: gender,
        height: Number(height),
        weight: Number(weight),
        systolic: Number(systolic),
        diastolic: Number(diastolic),
        cholesterol: Number(cholesterol),
        glucose: Number(glucose),
        smoking: Number(smoking),
        alcohol: Number(alcohol),
        physical: Number(physical)
    };

    fetch('/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(resp => resp.json())
    .then(data => {
        if (data.error) {
            resultDiv.innerHTML = `<p style="color: red;">Error: ${data.error}</p>`;
            return;
        }
        const prob = data.probability;
        const report = data.report || '';
        let riskLevel, riskMessage, riskColor;
        if (prob < 0.3) {
            riskLevel = "Low Risk";
            riskColor = "#2e8b57";
        } else if (prob < 0.7) {
            riskLevel = "Medium Risk";
            riskColor = "#ff8c00";
        } else {
            riskLevel = "High Risk";
            riskColor = "#dc143c";
        }

        // Display results
        resultDiv.innerHTML = `
            <div>
                <h3 style="color: ${riskColor}; margin-bottom: 6px;">Risk Assessment: ${riskLevel}</h3>
                <p><strong>Predicted probability:</strong> ${(prob*100).toFixed(1)}%</p>
                <div style="margin-top:8px; white-space:pre-wrap;">${report}</div>
            </div>
        `;
        resultDiv.classList.add('highlight');
    })
    .catch(err => {
        resultDiv.innerHTML = `<p style="color: red;">Request failed: ${err}</p>`;
    });
});