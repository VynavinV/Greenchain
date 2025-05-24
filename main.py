
#Import flask
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from google import genai as genai_sdk
from google.genai import types
import os # For secret key
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

#Initialize all variables
API_KEY = os.getenv("GOOGLE_AI_API_KEY", "#######") # Your API Key

# Initialize the genai client with your API key.
client = genai_sdk.Client(api_key=API_KEY)

# Create a Flask application
app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for session management

# System instructions for the AI
PATIENT_SYSTEM_INSTRUCTION = """You are MediBot, an AI medical assistant designed to provide general wellness guidance and support.

Your role:
1. Acknowledge the patient's concerns with empathy and understanding
2. Ask relevant follow-up questions to better understand their situation
3. Provide general wellness advice and self-care recommendations
4. Suggest when to seek professional medical attention

Guidelines:
- Be conversational, friendly, and supportive
- Ask clarifying questions about symptoms, duration, and medical history
- Do NOT provide medical diagnoses or prescribe prescription medications
- Suggest appropriate over-the-counter products when relevant (e.g., "consider a mild pain reliever like acetaminophen")
- Provide clear guidance on when to see a healthcare professional
- For emergencies, immediately advise contacting emergency services
- Keep responses concise but informative
- Always remind users that you provide general guidance, not medical diagnosis

When you have gathered sufficient information, provide a wellness plan that includes:
- Immediate self-care steps
- Lifestyle recommendations
- Suggested over-the-counter products (if appropriate)
- Clear indicators for when to seek professional medical help

Start your final wellness plan with "PRELIMINARY WELLNESS PLAN:" so the system can format it properly."""

DOCTOR_SUMMARY_SYSTEM_INSTRUCTION = """You are MediBot, an AI medical assistant. Your task is to generate a concise summary of a patient's provided information for a healthcare professional. The summary should include:
1. Key symptoms and their stated duration.
2. Relevant medical history, including any mentioned allergies.
3. Patient's stated preferences or concerns, if any.
4. Highlight any information that seems critical or requires prompt attention.
Do not add any conversational fluff. Provide only the summary based on the chat history."""

MODEL_NAME = "gemini-1.5-flash"

#Home route (Patient Input Page)
@app.route('/')
def home():
    session.pop('chat_history', None) 
    session.pop('full_chat_log', None) 
    session.pop('patient_details', None)
    session.pop('dynamic_questions', None)
    session.pop('question_answers', None)
    return render_template('patient_form.html')

# Patient Details Form Submission
@app.route('/submit_details', methods=['POST'])
def submit_patient_details():
    try:
        patient_details = {
            'name': request.form.get('name'),
            'age': request.form.get('age'),
            'gender': request.form.get('gender'),
            'primary_symptoms': request.form.get('primary_symptoms'),
            'symptom_duration': request.form.get('symptom_duration'),
            'pain_level': request.form.get('pain_level'),
            'medical_history': request.form.get('medical_history'),
            'current_medications': request.form.get('current_medications'),
            'allergies': request.form.get('allergies'),
            'lifestyle_factors': request.form.get('lifestyle_factors')
        }
        
        session['patient_details'] = patient_details
        
        # Generate dynamic questions based on patient details
        questions = generate_dynamic_questions(patient_details)
        session['dynamic_questions'] = questions
        
        return redirect(url_for('dynamic_questionnaire'))
        
    except Exception as e:
        app.logger.error(f"Error processing patient details: {e}")
        return jsonify({'error': 'Failed to process patient details'}), 500

def generate_dynamic_questions(patient_details):
    """Generate personalized questions based on patient's initial details"""
    prompt = f"""Based on the following patient information, generate 5-8 specific follow-up questions to better understand their condition:

Patient Details:
- Name: {patient_details['name']}
- Age: {patient_details['age']}
- Gender: {patient_details['gender']}
- Primary Symptoms: {patient_details['primary_symptoms']}
- Duration: {patient_details['symptom_duration']}
- Pain Level: {patient_details['pain_level']}/10
- Medical History: {patient_details['medical_history']}
- Current Medications: {patient_details['current_medications']}
- Allergies: {patient_details['allergies']}

Generate questions that would help a medical professional better understand the patient's condition. 
Return ONLY a valid JSON array of objects with this exact format:
[
    {{
        "id": "q1",
        "question": "Question text here",
        "type": "text",
        "required": true
    }},
    {{
        "id": "q2", 
        "question": "Question text here",
        "type": "select",
        "options": ["Option1", "Option2", "Option3"],
        "required": true
    }}
]

Question types can be: "text", "select", "number", "textarea"
Make questions specific to their symptoms and medical history."""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[types.Content(role='user', parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                candidate_count=1,
                system_instruction="You are a medical assistant. Generate only valid JSON. No additional text."
            ),
        )
        
        import json
        questions_json = response.text.strip()
        # Clean up the response to ensure it's valid JSON
        if questions_json.startswith('```json'):
            questions_json = questions_json.replace('```json', '').replace('```', '').strip()
        
        questions = json.loads(questions_json)
        return questions
        
    except Exception as e:
        app.logger.error(f"Error generating questions: {e}")
        # Fallback questions
        return [
            {
                "id": "q1",
                "question": "Can you describe when your symptoms are worst?",
                "type": "text",
                "required": True
            },
            {
                "id": "q2",
                "question": "Have you tried any treatments or remedies?",
                "type": "textarea",
                "required": False
            }
        ]

# Chat API endpoint
@app.route('/chat', methods=['POST'])
def chat_endpoint():
    data = request.json
    user_message_text = data.get('message')

    if not user_message_text:
        return jsonify({'error': 'No message provided'}), 400

    if 'chat_history' not in session:
        session['chat_history'] = [] 
        session['full_chat_log'] = [] 

    # Convert chat history to proper format for Google GenAI
    formatted_contents = []
    for message in session['chat_history']:
        if message['role'] == 'user':
            formatted_contents.append(types.Content(role='user', parts=[types.Part(text=message['parts'][0])]))
        else:
            formatted_contents.append(types.Content(role='model', parts=[types.Part(text=message['parts'][0])]))
    
    # Add current user message
    formatted_contents.append(types.Content(role='user', parts=[types.Part(text=user_message_text)]))
    session['chat_history'].append({'role': 'user', 'parts': [user_message_text]})
    session['full_chat_log'].append(f"Patient: {user_message_text}")

    try:
        # Generate content using the client
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=formatted_contents,
            config=types.GenerateContentConfig(
                candidate_count=1,
                system_instruction=PATIENT_SYSTEM_INSTRUCTION
            ),
        )
        ai_response_text = response.text

        session['chat_history'].append({'role': 'model', 'parts': [ai_response_text]})
        session['full_chat_log'].append(f"MediBot: {ai_response_text}")
        session.modified = True

        if "PRELIMINARY WELLNESS PLAN:" in ai_response_text:
            return jsonify({'response': ai_response_text, 'action': 'show_plan'})
        else:
            return jsonify({'response': ai_response_text})

    except Exception as e:
        app.logger.error(f"Error during AI chat: {e}")
        # More specific error checking for API key issues or other common problems
        if "API key not valid" in str(e) or "API_KEY_INVALID" in str(e) or "permission_denied" in str(e).lower():
             return jsonify({'error': 'AI service API key is invalid or lacks permissions. Please check server configuration.'}), 500
        return jsonify({'error': f"An unexpected error occurred with the AI service: {str(e)}"}), 500

# Dynamic Questionnaire Page
@app.route('/questionnaire')
def dynamic_questionnaire():
    if 'dynamic_questions' not in session:
        return redirect(url_for('home'))
    return render_template('questionnaire.html', questions=session['dynamic_questions'])

# Submit Dynamic Questionnaire
@app.route('/submit_questionnaire', methods=['POST'])
def submit_questionnaire():
    try:
        answers = {}
        for question in session['dynamic_questions']:
            answer = request.form.get(question['id'])
            answers[question['id']] = {
                'question': question['question'],
                'answer': answer
            }
        
        session['question_answers'] = answers
        
        # Generate treatment plan
        treatment_plan = generate_treatment_plan()
        session['treatment_plan'] = treatment_plan
        
        return redirect(url_for('treatment_plan_view'))
        
    except Exception as e:
        app.logger.error(f"Error processing questionnaire: {e}")
        return jsonify({'error': 'Failed to process questionnaire'}), 500

def generate_treatment_plan():
    """Generate comprehensive treatment plan based on all collected data"""
    patient_details = session.get('patient_details', {})
    question_answers = session.get('question_answers', {})
    
    # Compile all information
    patient_summary = f"""
Patient Information:
- Name: {patient_details.get('name')}
- Age: {patient_details.get('age')}
- Gender: {patient_details.get('gender')}
- Primary Symptoms: {patient_details.get('primary_symptoms')}
- Duration: {patient_details.get('symptom_duration')}
- Pain Level: {patient_details.get('pain_level')}/10
- Medical History: {patient_details.get('medical_history')}
- Current Medications: {patient_details.get('current_medications')}
- Allergies: {patient_details.get('allergies')}
- Lifestyle: {patient_details.get('lifestyle_factors')}

Follow-up Questions and Answers:
"""
    
    for answer_data in question_answers.values():
        patient_summary += f"Q: {answer_data['question']}\nA: {answer_data['answer']}\n\n"
    
    prompt = f"""Based on this comprehensive patient information, generate a detailed treatment plan in JSON format:

{patient_summary}

Generate a treatment plan with the following structure (return ONLY valid JSON):
{{
    "patient_summary": {{
        "condition": "Brief description of likely condition",
        "severity": "Low/Moderate/High",
        "urgency": "Routine/Urgent/Emergency"
    }},
    "immediate_care": [
        {{
            "action": "Action to take",
            "description": "Detailed description",
            "icon": "fas fa-icon-name"
        }}
    ],
    "medications": [
        {{
            "name": "Medication name",
            "dosage": "Dosage instructions",
            "frequency": "How often",
            "duration": "How long",
            "type": "OTC/Prescription",
            "icon": "fas fa-pills"
        }}
    ],
    "lifestyle_recommendations": [
        {{
            "category": "Diet/Exercise/Sleep/etc",
            "recommendation": "Specific recommendation",
            "icon": "fas fa-icon-name"
        }}
    ],
    "warning_signs": [
        {{
            "sign": "Warning sign to watch for",
            "action": "What to do if this occurs",
            "icon": "fas fa-exclamation-triangle"
        }}
    ],
    "follow_up": {{
        "timeline": "When to follow up",
        "with_whom": "Primary care, specialist, etc",
        "reason": "Why follow up is needed"
    }},
    "emergency_contacts": [
        {{
            "service": "Emergency/Urgent Care/Doctor",
            "when_to_call": "Circumstances",
            "number": "Contact information"
        }}
    ]
}}

Focus on safe, general wellness recommendations. Do not diagnose specific conditions."""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[types.Content(role='user', parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(
                candidate_count=1,
                system_instruction="You are a medical assistant. Generate comprehensive but safe treatment recommendations. Return only valid JSON."
            ),
        )
        
        plan_json = response.text.strip()
        if plan_json.startswith('```json'):
            plan_json = plan_json.replace('```json', '').replace('```', '').strip()
        
        treatment_plan = json.loads(plan_json)
        #Save the treatment plan in /patient_details folder
        with open(f"patient_details/{patient_details['name']}_treatment_plan.json", "w") as f:
            json.dump(treatment_plan, f, indent=4)
        # Log the treatment plan
        return treatment_plan
        
    except Exception as e:
        app.logger.error(f"Error generating treatment plan: {e}")
        # Fallback treatment plan
        return {
            "patient_summary": {
                "condition": "General wellness consultation needed",
                "severity": "Moderate",
                "urgency": "Routine"
            },
            "immediate_care": [
                {
                    "action": "Rest and monitor symptoms",
                    "description": "Take adequate rest and keep track of symptom changes",
                    "icon": "fas fa-bed"
                }
            ],
            "medications": [],
            "lifestyle_recommendations": [
                {
                    "category": "General Health",
                    "recommendation": "Maintain a balanced diet and regular exercise",
                    "icon": "fas fa-heart"
                }
            ],
            "warning_signs": [
                {
                    "sign": "Symptoms worsen significantly",
                    "action": "Contact healthcare provider immediately",
                    "icon": "fas fa-exclamation-triangle"
                }
            ],
            "follow_up": {
                "timeline": "1-2 weeks",
                "with_whom": "Primary care physician",
                "reason": "Monitor symptom progression"
            },
            "emergency_contacts": [
                {
                    "service": "Emergency Services",
                    "when_to_call": "Life-threatening emergency",
                    "number": "911"
                }
            ]
        }

# Treatment Plan Page
@app.route('/treatment')
def treatment_plan_view():
    if 'treatment_plan' not in session:
        return redirect(url_for('home'))
    
    treatment_plan = session['treatment_plan']
    patient_details = session.get('patient_details', {})
    
    return render_template('treatment_plan.html', 
                         treatment_plan=treatment_plan, 
                         patient_details=patient_details)

#Doctor Summary Page
@app.route('/doctor_summary')
def doctor_summary():
    #Get json data from the patuent_details folder and return a list of patient names and their treatment plans
    patient_files = os.listdir('patient_details')
    patient_names = []
    for file in patient_files:
        if file.endswith('_treatment_plan.json'):
            patient_name = file.split('_')[0]
            patient_names.append(patient_name)
    return render_template('doctor_summary.html', patient_names=patient_names)

# Doctor: View patient treatment plan in detail (like patient view)
@app.route('/doctor/patient/<patient_name>')
def doctor_patient_view(patient_name):
    # Load the treatment plan JSON for the given patient
    file_path = os.path.join('patient_details', f'{patient_name}_treatment_plan.json')
    if not os.path.exists(file_path):
        return f"No treatment plan found for {patient_name}", 404
    with open(file_path, 'r') as f:
        treatment_plan = json.load(f)
    return render_template('doctor_patient_view.html', treatment_plan=treatment_plan, patient_name=patient_name)

#Run the app
if __name__ == '__main__':
    app.run(debug=True)
