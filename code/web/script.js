document.getElementById('predictionForm').addEventListener('submit', function(e) {
    e.preventDefault();


    const age = document.getElementById('age').value;
    const height = document.getElementById('height').value;
    const weight = document.getElementById('weight').value;
    const systolic = document.getElementById('systolic').value;
    const diastolic = document.getElementById('diastolic').value;
    const cholesterol = document.getElementById('cholesterol').value;
    const glucose = document.getElementById('glucose').value;
    const smoking = document.getElementById('smoking').value;
    const alcohol = document.getElementById('alcohol').value;
    const physical = document.getElementById('physical').value;


    if (!age || !height || !weight || !systolic || !diastolic ||
        !cholesterol || !glucose || !smoking || !alcohol || !physical) {
        alert('Please fill in all fields');
        return;
    }

    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing data...';
    resultDiv.classList.remove('highlight');


    // Convert frontend fields into a list for direct prediction
    // Order: [age_years, bmi, ap_hi, ap_lo, cholesterol, gluc, active]
    const h_m = Number(height) / 100.0;
    const bmi = h_m > 0 ? Number(weight) / (h_m * h_m) : 0;

    const payload = [
        Number(age),           // age_years
        Number(bmi.toFixed(2)), // bmi
        Number(systolic),      // ap_hi
        Number(diastolic),     // ap_lo
        Number(cholesterol),   // cholesterol
        Number(glucose),       // gluc
        Number(physical)       // active
    ];

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
        // Display the probability from backend
        const prob = data.probability;
        const recommendations = data.recommendations || "No recommendations available.";
        let riskLevel, riskMessage, riskColor;
        if (prob < 0.3) {
            riskLevel = "Low Risk";
            riskMessage = `Predicted probability: ${(prob * 100).toFixed(2)}%. Your cardiovascular disease risk is low.`;
            riskColor = "#2e8b57";
        } else if (prob < 0.7) {
            riskLevel = "Medium Risk";
            riskMessage = `Predicted probability: ${(prob * 100).toFixed(2)}%. You have a moderate risk.`;
            riskColor = "#ff8c00";
        } else {
            riskLevel = "High Risk";
            riskMessage = `Predicted probability: ${(prob * 100).toFixed(2)}%. Your risk is high.`;
            riskColor = "#dc143c";
        }
        resultDiv.innerHTML = `
            <div>
                <h3 style="color: ${riskColor}; margin-bottom: 10px;">Risk Assessment: ${riskLevel}</h3>
                <p>${riskMessage}</p>
                <div style="margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
                    <h4 style="margin-bottom: 8px; color: #333;">Personalized Recommendations:</h4>
                    <p style="line-height: 1.5; color: #555;">${recommendations.replace(/\n/g, '<br>')}</p>
                </div>
            </div>
        `;
        resultDiv.classList.add('highlight');
    })
    .catch(err => {
        resultDiv.innerHTML = `<p style="color:red">Request failed: ${err}</p>`;
    });
});