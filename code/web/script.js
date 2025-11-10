document.getElementById('predictionForm').addEventListener('submit', function(e) {
    e.preventDefault();


    const age = document.getElementById('age').value;
    const gender = document.getElementById('gender').value;
    const height = document.getElementById('height').value;
    const weight = document.getElementById('weight').value;
    const systolic = document.getElementById('systolic').value;
    const diastolic = document.getElementById('diastolic').value;
    const cholesterol = document.getElementById('cholesterol').value;
    const glucose = document.getElementById('glucose').value;
    const smoking = document.getElementById('smoking').value;
    const alcohol = document.getElementById('alcohol').value;
    const physical = document.getElementById('physical').value;


    if (!age || !gender || !height || !weight || !systolic || !diastolic ||
        !cholesterol || !glucose || !smoking || !alcohol || !physical) {
        alert('Please fill in all fields');
        return;
    }

    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing data...';
    resultDiv.classList.remove('highlight');


    setTimeout(() => {
        // Simulate risk assessment (in a real app, this would call a backend API)
        const riskScore = Math.random();
        let riskLevel, riskMessage, riskColor;

        if (riskScore < 0.3) {
            riskLevel = "Low Risk";
            riskMessage = "Based on the data provided, your cardiovascular disease risk is low. Keep maintaining a healthy lifestyle!";
            riskColor = "#2e8b57";
        } else if (riskScore < 0.7) {
            riskLevel = "Medium Risk";
            riskMessage = "Based on the data provided, you have a moderate cardiovascular disease risk. Regular check-ups and attention to lifestyle are recommended.";
            riskColor = "#ff8c00";
        } else {
            riskLevel = "High Risk";
            riskMessage = "Based on the data provided, your cardiovascular disease risk is high. It is recommended to consult a healthcare professional as soon as possible.";
            riskColor = "#dc143c";
        }

        // Display results
        resultDiv.innerHTML = `
            <div>
                <h3 style="color: ${riskColor}; margin-bottom: 10px;">Risk Assessment: ${riskLevel}</h3>
                <p>${riskMessage}</p>
            </div>
        `;
        resultDiv.classList.add('highlight');
    }, 2000);


    const payload = {
        age_years: Number(age),            // send as age_years so main.py recognizes it
        gender: gender,                    // string, main._gender_code will map it
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
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            resultDiv.innerHTML = `<p style="color:red">Error: ${data.error}</p>`;
            return;
        }
        // show probability/report as your current script already does
    })
    .catch(err => {
        resultDiv.innerHTML = `<p style="color:red">Request failed: ${err}</p>`;
    });
});