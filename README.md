# Cardiovascular Disease Risk Prediction Web App

A web application for predicting cardiovascular disease risk using machine learning.

## Project Structure

```
ie0005_mini_project/
├── README.md                          # Project documentation
├── code/
│   ├── cardio_prediction_model.pkl    # Trained ML model (pickle)
│   ├── prediction_core.py             # Core prediction functions
│   ├── main.py                        # Legacy processing script
│   ├── server.py                      # Flask web server
│   ├── api_para.json                  # API parameters (optional)
│   ├── credentials.json               # API credentials (optional)
│   └── web/
│       ├── webpage.html               # Frontend HTML
│       ├── script.js                  # Frontend JavaScript
│       ├── style.css                  # Frontend CSS
│       └── image/                     # Static images
├── eda/
│   ├── cardio_train.csv               # Original dataset
│   ├── cleaned_data.xlsx              # Cleaned data
│   ├── eda_cardio.ipynb               # EDA notebook
│   ├── model.ipynb                    # Model training notebook
│   └── graph/                         # EDA plots
└── .gitignore                         # Git ignore file
```

## Features

- **Web Interface**: User-friendly form for inputting health data
- **Real-time Prediction**: Instant cardiovascular risk assessment
- **Machine Learning**: Logistic regression model trained on health data
- **Responsive Design**: Modern UI with risk visualization

## Input Features

The model predicts based on 7 health features:
1. **Age** (years)
2. **BMI** (calculated from height/weight)
3. **Systolic BP** (mmHg)
4. **Diastolic BP** (mmHg)
5. **Cholesterol Level** (1-3 scale)
6. **Glucose Level** (1-3 scale)
7. **Physical Activity** (0/1)

## Installation & Setup

### Prerequisites
- Python 3.8+
- Conda (recommended for environment management)

### 1. Clone Repository
```bash
git clone <repository-url>
cd ie0005_mini_project
```

### 2. Create Environment
```bash
conda create -n cardio-pred python=3.10
conda activate cardio-pred
```

### 3. Install Dependencies
```bash
conda install flask pandas scikit-learn joblib
```

### 4. Ensure Model File
Make sure `code/cardio_prediction_model.pkl` exists (trained from `eda/model.ipynb`).

## Running the Application

### Start the Server
```bash
cd code
python server.py
```

The server will start on `http://localhost:11451` (or check console output).

### Access the Web App
Open your browser and go to: `http://localhost:11451`

### Test the API
```bash
curl -X POST http://localhost:11451/submit \
  -H "Content-Type: application/json" \
  -d "[50, 25.0, 120, 80, 2, 1, 1]"
```

Expected response: `{"probability": 0.3865}`

## API Endpoints

- `GET /` - Main web page
- `POST /submit` - Prediction endpoint
  - Input: JSON array `[age, bmi, systolic, diastolic, cholesterol, glucose, activity]`
  - Output: `{"probability": float}` or `{"error": "message"}`

## Development

### Training the Model
1. Open `eda/model.ipynb`
2. Run all cells to train and save the model
3. The `cardio_prediction_model.pkl` will be saved to `code/`

### Modifying the Web Interface
- HTML: `code/web/webpage.html`
- CSS: `code/web/style.css`
- JavaScript: `code/web/script.js`

### Adding Features
- Edit `prediction_core.py` for new prediction logic
- Modify `server.py` for new API endpoints

## Data Source

The model is trained on cardiovascular disease data with features like age, blood pressure, cholesterol, etc.

## Security Notes

- API keys are stored in `credentials.json` (gitignored)
- No user data is stored permanently
- All processing happens in-memory

## Troubleshooting

### Server Won't Start
- Check if port 11451 is available
- Ensure all dependencies are installed
- Verify `cardio_prediction_model.pkl` exists

### Model Errors
- Re-run `eda/model.ipynb` to regenerate the model
- Check input data format matches expected features

### Frontend Issues
- Clear browser cache
- Check browser console for JavaScript errors

## License

This project is for educational purposes.