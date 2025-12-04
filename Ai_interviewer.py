"""
AI Interviewer Bot - Professional Interview System
Conducts technical interviews based on candidate's resume
"""

import streamlit as st
import openai
from PyPDF2 import PdfReader
import json
from typing import Dict, List, Tuple
import re

# Page configuration
st.set_page_config(
    page_title="AI Interviewer Bot",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #374151;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #e5e7eb;
        padding-bottom: 0.5rem;
    }
    .question-box {
        background-color: #f9fafb;
        border-left: 4px solid #3b82f6;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 0.5rem;
    }
    .answer-box {
        background-color: #f0f9ff;
        border-left: 4px solid #0ea5e9;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 0.5rem;
    }
    .score-box {
        background-color: #ecfdf5;
        border: 2px solid #10b981;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .feedback-box {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 0.5rem;
    }
    .selected {
        background-color: #dcfce7;
        border: 3px solid #16a34a;
        padding: 1.5rem;
        border-radius: 0.5rem;
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
        color: #166534;
    }
    .rejected {
        background-color: #fee2e2;
        border: 3px solid #dc2626;
        padding: 1.5rem;
        border-radius: 0.5rem;
        text-align: center;
        font-size: 1.5rem;
        font-weight: 700;
        color: #991b1b;
    }
    .stButton>button {
        width: 100%;
        background-color: #3b82f6;
        color: white;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        border-radius: 0.5rem;
        border: none;
        transition: background-color 0.3s;
    }
    .stButton>button:hover {
        background-color: #2563eb;
    }
    .info-card {
        background-color: #eff6ff;
        border: 1px solid #dbeafe;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    """Initialize all session state variables"""
    if 'api_key' not in st.session_state:
        st.session_state.api_key = ""
    if 'resume_processed' not in st.session_state:
        st.session_state.resume_processed = False
    if 'candidate_profile' not in st.session_state:
        st.session_state.candidate_profile = {}
    if 'current_question_num' not in st.session_state:
        st.session_state.current_question_num = 0
    if 'questions' not in st.session_state:
        st.session_state.questions = []
    if 'answers' not in st.session_state:
        st.session_state.answers = []
    if 'scores' not in st.session_state:
        st.session_state.scores = []
    if 'interview_complete' not in st.session_state:
        st.session_state.interview_complete = False
    if 'current_question' not in st.session_state:
        st.session_state.current_question = ""
    if 'final_report' not in st.session_state:
        st.session_state.final_report = {}

def extract_text_from_pdf(pdf_file) -> str:
    """Extract text content from uploaded PDF file"""
    try:
        pdf_reader = PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

def analyze_resume(resume_text: str, api_key: str) -> Dict:
    """
    Analyze resume to extract candidate profile including skills, domain, and experience
    """
    client = openai.OpenAI(api_key=api_key)
    
    prompt = f"""You are an expert recruiter and technical interviewer. Analyze the following resume and extract key information.

Resume Content:
{resume_text}

Provide a structured analysis in JSON format with the following fields:
1. candidate_name: The candidate's name
2. domain: Primary domain/field (e.g., Data Science, Software Engineering, DevOps)
3. experience_level: Junior/Mid-Level/Senior based on years of experience
4. key_skills: List of 5-7 most important technical skills
5. projects: List of 2-3 significant projects with brief descriptions
6. expertise_areas: Specific areas of expertise within their domain
7. years_of_experience: Estimated years of professional experience

Return ONLY valid JSON without any additional text or markdown formatting.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert resume analyzer. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        content = re.sub(r'```json\s*|\s*```', '', content)
        
        profile = json.loads(content)
        return profile
    except json.JSONDecodeError as e:
        st.error(f"Error parsing resume analysis: {str(e)}")
        return {}
    except Exception as e:
        st.error(f"Error analyzing resume: {str(e)}")
        return {}

def generate_interview_questions(candidate_profile: Dict, api_key: str) -> List[str]:
    """
    Generate 3 technical interview questions based on candidate's profile
    """
    client = openai.OpenAI(api_key=api_key)
    
    prompt = f"""You are an expert technical interviewer. Based on the candidate's profile, generate 3 progressive interview questions.

Candidate Profile:
- Name: {candidate_profile.get('candidate_name', 'Unknown')}
- Domain: {candidate_profile.get('domain', 'Unknown')}
- Experience Level: {candidate_profile.get('experience_level', 'Unknown')}
- Key Skills: {', '.join(candidate_profile.get('key_skills', []))}
- Expertise Areas: {', '.join(candidate_profile.get('expertise_areas', []))}
- Years of Experience: {candidate_profile.get('years_of_experience', 'Unknown')}

Requirements:
1. Generate exactly 3 questions that progressively increase in difficulty
2. Question 1: Fundamental concept related to their primary skill
3. Question 2: Practical application or scenario-based question
4. Question 3: Advanced problem-solving or system design question
5. Questions should be relevant to their domain and expertise
6. Each question should be clear, specific, and test deep understanding

Return the questions in JSON format as an array:
["question1", "question2", "question3"]

Return ONLY valid JSON without any additional text or markdown formatting.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        content = re.sub(r'```json\s*|\s*```', '', content)
        
        questions = json.loads(content)
        return questions
    except json.JSONDecodeError as e:
        st.error(f"Error parsing questions: {str(e)}")
        return []
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return []

def evaluate_answer(question: str, answer: str, candidate_profile: Dict, api_key: str) -> Tuple[int, str]:
    """
    Evaluate candidate's answer and provide score (1-5) with detailed feedback
    """
    client = openai.OpenAI(api_key=api_key)
    
    prompt = f"""You are an expert technical interviewer evaluating a candidate's response.

Candidate Profile:
- Domain: {candidate_profile.get('domain', 'Unknown')}
- Experience Level: {candidate_profile.get('experience_level', 'Unknown')}
- Key Skills: {', '.join(candidate_profile.get('key_skills', []))}

Question Asked:
{question}

Candidate's Answer:
{answer}

Evaluate the answer based on:
1. Technical accuracy and correctness
2. Depth of understanding
3. Clarity of explanation
4. Practical knowledge and real-world applicability
5. Completeness of the answer

Provide evaluation in JSON format:
{{
    "score": <integer between 1-5>,
    "feedback": "<detailed feedback explaining the score, highlighting strengths and areas for improvement>"
}}

Score Guidelines:
- 5: Excellent - Comprehensive, accurate, demonstrates deep understanding
- 4: Good - Mostly accurate with good understanding, minor gaps
- 3: Satisfactory - Basic understanding, some inaccuracies or incompleteness
- 2: Below Average - Significant gaps in understanding or accuracy
- 1: Poor - Incorrect or demonstrates lack of fundamental understanding

Return ONLY valid JSON without any additional text or markdown formatting.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        content = re.sub(r'```json\s*|\s*```', '', content)
        
        evaluation = json.loads(content)
        return evaluation.get('score', 3), evaluation.get('feedback', 'No feedback available')
    except json.JSONDecodeError as e:
        st.error(f"Error parsing evaluation: {str(e)}")
        return 3, "Error in evaluation"
    except Exception as e:
        st.error(f"Error evaluating answer: {str(e)}")
        return 3, "Error in evaluation"

def generate_final_report(candidate_profile: Dict, questions: List[str], answers: List[str], 
                         scores: List[Tuple[int, str]], api_key: str) -> Dict:
    """
    Generate comprehensive final report with overall assessment and recommendation
    """
    client = openai.OpenAI(api_key=api_key)
    
    # Calculate average score
    avg_score = sum(score for score, _ in scores) / len(scores) if scores else 0
    
    # Prepare Q&A summary
    qa_summary = ""
    for i, (q, a, (score, feedback)) in enumerate(zip(questions, answers, scores), 1):
        qa_summary += f"\nQuestion {i}: {q}\n"
        qa_summary += f"Answer: {a[:200]}...\n"
        qa_summary += f"Score: {score}/5\n"
        qa_summary += f"Feedback: {feedback}\n"
    
    prompt = f"""You are a senior technical hiring manager providing a final interview assessment.

Candidate Profile:
- Name: {candidate_profile.get('candidate_name', 'Unknown')}
- Domain: {candidate_profile.get('domain', 'Unknown')}
- Experience Level: {candidate_profile.get('experience_level', 'Unknown')}
- Key Skills: {', '.join(candidate_profile.get('key_skills', []))}

Interview Performance:
Average Score: {avg_score:.2f}/5
{qa_summary}

Provide a comprehensive final assessment in JSON format:
{{
    "overall_assessment": "<2-3 paragraph overall assessment of candidate's performance>",
    "strengths": ["strength1", "strength2", "strength3"],
    "areas_for_improvement": ["area1", "area2", "area3"],
    "technical_competency": "<assessment of technical skills>",
    "recommendation": "SELECTED" or "NOT_SELECTED",
    "recommendation_rationale": "<clear rationale for the decision>",
    "suggested_next_steps": "<if selected: next steps; if not: guidance for improvement>"
}}

Selection Criteria:
- Average Score >= 3.5: Strong candidate for SELECTED
- Average Score 2.5-3.4: Borderline, consider other factors
- Average Score < 2.5: NOT_SELECTED

Return ONLY valid JSON without any additional text or markdown formatting.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a senior hiring manager. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        
        content = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        content = re.sub(r'```json\s*|\s*```', '', content)
        
        report = json.loads(content)
        report['average_score'] = avg_score
        return report
    except json.JSONDecodeError as e:
        st.error(f"Error parsing final report: {str(e)}")
        return {"recommendation": "ERROR", "average_score": avg_score}
    except Exception as e:
        st.error(f"Error generating final report: {str(e)}")
        return {"recommendation": "ERROR", "average_score": avg_score}

def reset_interview():
    """Reset all interview-related session state"""
    st.session_state.resume_processed = False
    st.session_state.candidate_profile = {}
    st.session_state.current_question_num = 0
    st.session_state.questions = []
    st.session_state.answers = []
    st.session_state.scores = []
    st.session_state.interview_complete = False
    st.session_state.current_question = ""
    st.session_state.final_report = {}

# Main Application
def main():
    initialize_session_state()
    
    # Header
    st.markdown('<div class="main-header">AI Interviewer Bot</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Intelligent Resume-Based Technical Interview System</div>', unsafe_allow_html=True)
    
    # API Key Input
    if not st.session_state.api_key:
        st.markdown('<div class="section-header">Configuration</div>', unsafe_allow_html=True)
        api_key_input = st.text_input("Enter OpenAI API Key", type="password", help="Your API key will not be stored permanently")
        
        if api_key_input:
            st.session_state.api_key = api_key_input
            st.success("API Key configured successfully")
            st.rerun()
        else:
            st.info("Please enter your OpenAI API key to begin")
            return
    
    # Main Application Flow
    if not st.session_state.interview_complete:
        # Step 1: Resume Upload and Processing
        if not st.session_state.resume_processed:
            st.markdown('<div class="section-header">Step 1: Upload Resume</div>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                uploaded_file = st.file_uploader("Upload Candidate Resume (PDF)", type=['pdf'])
                
                if uploaded_file is not None:
                    with st.spinner("Processing resume..."):
                        # Extract text from PDF
                        resume_text = extract_text_from_pdf(uploaded_file)
                        
                        if resume_text:
                            # Analyze resume
                            candidate_profile = analyze_resume(resume_text, st.session_state.api_key)
                            
                            if candidate_profile:
                                st.session_state.candidate_profile = candidate_profile
                                
                                # Generate interview questions
                                questions = generate_interview_questions(candidate_profile, st.session_state.api_key)
                                
                                if questions and len(questions) == 3:
                                    st.session_state.questions = questions
                                    st.session_state.current_question = questions[0]
                                    st.session_state.resume_processed = True
                                    st.success("Resume processed successfully! Interview ready to begin.")
                                    st.rerun()
                                else:
                                    st.error("Failed to generate interview questions. Please try again.")
                        else:
                            st.error("Failed to extract text from PDF. Please ensure the file is readable.")
        
        # Step 2: Conduct Interview
        else:
            # Display Candidate Profile
            st.markdown('<div class="section-header">Candidate Profile</div>', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown('<div class="info-card">', unsafe_allow_html=True)
                st.markdown(f"**Name:** {st.session_state.candidate_profile.get('candidate_name', 'N/A')}")
                st.markdown(f"**Domain:** {st.session_state.candidate_profile.get('domain', 'N/A')}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="info-card">', unsafe_allow_html=True)
                st.markdown(f"**Experience:** {st.session_state.candidate_profile.get('experience_level', 'N/A')}")
                st.markdown(f"**Years:** {st.session_state.candidate_profile.get('years_of_experience', 'N/A')}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col3:
                st.markdown('<div class="info-card">', unsafe_allow_html=True)
                skills = st.session_state.candidate_profile.get('key_skills', [])
                st.markdown(f"**Key Skills:** {', '.join(skills[:3])}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Interview Progress
            st.markdown('<div class="section-header">Interview Progress</div>', unsafe_allow_html=True)
            progress = st.session_state.current_question_num / 3
            st.progress(progress)
            st.markdown(f"**Question {st.session_state.current_question_num + 1} of 3**")
            
            # Display Current Question
            st.markdown('<div class="question-box">', unsafe_allow_html=True)
            st.markdown(f"**Question {st.session_state.current_question_num + 1}:**")
            st.markdown(st.session_state.current_question)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Answer Input
            answer = st.text_area(
                "Your Answer",
                height=200,
                placeholder="Type your answer here...",
                key=f"answer_{st.session_state.current_question_num}"
            )
            
            # Submit Answer Button
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("Submit Answer", type="primary"):
                    if answer.strip():
                        with st.spinner("Evaluating your answer..."):
                            # Evaluate the answer
                            score, feedback = evaluate_answer(
                                st.session_state.current_question,
                                answer,
                                st.session_state.candidate_profile,
                                st.session_state.api_key
                            )
                            
                            # Store answer and score
                            st.session_state.answers.append(answer)
                            st.session_state.scores.append((score, feedback))
                            
                            # Move to next question or complete interview
                            st.session_state.current_question_num += 1
                            
                            if st.session_state.current_question_num < 3:
                                st.session_state.current_question = st.session_state.questions[st.session_state.current_question_num]
                                st.success(f"Answer submitted! Score: {score}/5")
                                st.rerun()
                            else:
                                # Interview complete - generate final report
                                with st.spinner("Generating final assessment..."):
                                    final_report = generate_final_report(
                                        st.session_state.candidate_profile,
                                        st.session_state.questions,
                                        st.session_state.answers,
                                        st.session_state.scores,
                                        st.session_state.api_key
                                    )
                                    st.session_state.final_report = final_report
                                    st.session_state.interview_complete = True
                                    st.rerun()
                    else:
                        st.warning("Please provide an answer before submitting.")
            
            # Display Previous Q&A
            if st.session_state.current_question_num > 0:
                with st.expander("View Previous Questions and Scores"):
                    for i in range(st.session_state.current_question_num):
                        st.markdown(f"**Question {i+1}:** {st.session_state.questions[i]}")
                        st.markdown(f"**Your Answer:** {st.session_state.answers[i][:200]}...")
                        score, feedback = st.session_state.scores[i]
                        st.markdown(f"**Score:** {score}/5")
                        st.markdown(f"**Feedback:** {feedback}")
                        st.markdown("---")
    
    # Step 3: Display Final Report
    else:
        st.markdown('<div class="section-header">Interview Complete</div>', unsafe_allow_html=True)
        
        report = st.session_state.final_report
        
        # Overall Score
        st.markdown(f"### Overall Performance Score: {report.get('average_score', 0):.2f}/5.00")
        st.progress(report.get('average_score', 0) / 5)
        
        # Selection Decision
        st.markdown('<div class="section-header">Decision</div>', unsafe_allow_html=True)
        recommendation = report.get('recommendation', 'ERROR')
        
        if recommendation == "SELECTED":
            st.markdown('<div class="selected">CANDIDATE SELECTED</div>', unsafe_allow_html=True)
        elif recommendation == "NOT_SELECTED":
            st.markdown('<div class="rejected">CANDIDATE NOT SELECTED</div>', unsafe_allow_html=True)
        else:
            st.error("Error in generating recommendation")
        
        # Detailed Assessment
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Strengths")
            for strength in report.get('strengths', []):
                st.markdown(f"- {strength}")
        
        with col2:
            st.markdown("#### Areas for Improvement")
            for area in report.get('areas_for_improvement', []):
                st.markdown(f"- {area}")
        
        # Overall Assessment
        st.markdown('<div class="section-header">Overall Assessment</div>', unsafe_allow_html=True)
        st.markdown(report.get('overall_assessment', 'No assessment available'))
        
        # Technical Competency
        st.markdown('<div class="section-header">Technical Competency</div>', unsafe_allow_html=True)
        st.markdown(report.get('technical_competency', 'No assessment available'))
        
        # Recommendation Rationale
        st.markdown('<div class="section-header">Recommendation Rationale</div>', unsafe_allow_html=True)
        st.markdown(report.get('recommendation_rationale', 'No rationale available'))
        
        # Suggested Next Steps
        st.markdown('<div class="section-header">Next Steps</div>', unsafe_allow_html=True)
        st.markdown(report.get('suggested_next_steps', 'No suggestions available'))
        
        # Individual Question Scores
        with st.expander("View Detailed Question-by-Question Analysis"):
            for i, (question, answer, (score, feedback)) in enumerate(
                zip(st.session_state.questions, st.session_state.answers, st.session_state.scores), 1
            ):
                st.markdown(f"### Question {i}")
                st.markdown(f"**Question:** {question}")
                st.markdown(f"**Answer:** {answer}")
                st.markdown(f"**Score:** {score}/5")
                st.markdown(f"**Feedback:** {feedback}")
                st.markdown("---")
        
        # Reset Button
        st.markdown('<div class="section-header">Start New Interview</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Conduct Another Interview", type="primary"):
                reset_interview()
                st.rerun()

if __name__ == "__main__":
    main()