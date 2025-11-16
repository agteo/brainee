// LearnAI Web Frontend JavaScript

let currentScreen = 'welcome-screen';
let currentLesson = null;
let questionStartTime = null;

// Toast Notification System
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icon = {
        'success': '✅',
        'error': '❌',
        'info': 'ℹ️',
        'warning': '⚠️'
    }[type] || 'ℹ️';

    toast.innerHTML = `<span class="toast-icon">${icon}</span><span class="toast-message">${message}</span>`;
    container.appendChild(toast);

    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);

    // Remove after duration
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => container.removeChild(toast), 300);
    }, duration);
}

// Screen management
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    const screen = document.getElementById(screenId);
    if (screen) {
        screen.classList.add('active');
        currentScreen = screenId;
    }
}

function showLoading(message = 'Loading...') {
    const overlay = document.getElementById('loading-overlay');
    const text = document.getElementById('loading-text');
    text.textContent = message;
    overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = 'none';
}

// API calls
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(`/api/${endpoint}`, options);
    const result = await response.json();
    
    if (!result.success) {
        throw new Error(result.error || 'API call failed');
    }
    
    return result;
}

// Diagnostic flow
let currentDiagnosticMCQ = null;
let diagnosticQuestionIndex = 0;
let diagnosticPreviousAnswers = [];
let diagnosticTotalQuestions = 5;
let diagnosticQuestionCache = {}; // Cache for preloaded questions

function startDiagnostic() {
    showScreen('diagnostic-screen');
    questionStartTime = Date.now();
    diagnosticQuestionIndex = 0;
    diagnosticPreviousAnswers = [];
    diagnosticQuestionCache = {}; // Clear cache when starting new diagnostic
    
    // Load first diagnostic MCQ immediately
    loadDiagnosticMCQ(0);
    
    // Preload remaining questions in the background (1-4)
    preloadDiagnosticQuestions();
}

async function preloadDiagnosticQuestions() {
    // Preload questions 1-4 in parallel (question 0 is already loading)
    const preloadPromises = [];
    for (let i = 1; i < 5; i++) {
        preloadPromises.push(loadDiagnosticMCQIntoCache(i));
    }
    
    // Don't await - let them load in background
    Promise.all(preloadPromises).then(() => {
        console.log('All diagnostic questions preloaded');
    }).catch(error => {
        console.warn('Some diagnostic questions failed to preload:', error);
        // Non-critical - we'll load on demand if cache misses
    });
}

async function loadDiagnosticMCQIntoCache(questionIndex) {
    // Skip if already cached
    if (diagnosticQuestionCache[questionIndex]) {
        return diagnosticQuestionCache[questionIndex];
    }
    
    try {
        const result = await apiCall('diagnostic', 'POST', {
            answer: '',
            question_index: questionIndex,
            previous_answers: diagnosticPreviousAnswers,
            hesitation_seconds: 0
        });
        
        if (result && result.result && result.result.next_mode === 'multiple_choice' && result.result.question_payload) {
            const questionData = result.result.question_payload;
            questionData.questionIndex = questionIndex;
            diagnosticQuestionCache[questionIndex] = questionData;
            diagnosticTotalQuestions = result.result.total_questions || 5;
            return questionData;
        }
    } catch (error) {
        console.warn(`Failed to preload question ${questionIndex + 1}:`, error);
        // Return null on error - will load on demand
        return null;
    }
}

async function loadDiagnosticMCQ(questionIndex) {
    // Check cache first
    if (diagnosticQuestionCache[questionIndex]) {
        console.log(`Using cached question ${questionIndex + 1}`);
        currentDiagnosticMCQ = diagnosticQuestionCache[questionIndex];
        displayDiagnosticMCQ(currentDiagnosticMCQ, questionIndex, diagnosticTotalQuestions);
        return;
    }
    
    showLoading(`Loading question ${questionIndex + 1}...`);
    
    try {
        // Get diagnostic MCQ (pass empty answer to get the question)
        const result = await apiCall('diagnostic', 'POST', {
            answer: '',
            question_index: questionIndex,
            previous_answers: diagnosticPreviousAnswers,
            hesitation_seconds: 0
        });
        
        console.log('Diagnostic result:', result); // Debug log
        
        if (result && result.result && result.result.next_mode === 'multiple_choice' && result.result.question_payload) {
            currentDiagnosticMCQ = result.result.question_payload;
            currentDiagnosticMCQ.questionIndex = questionIndex;
            diagnosticTotalQuestions = result.result.total_questions || 5;
            
            // Cache the question for future use
            diagnosticQuestionCache[questionIndex] = currentDiagnosticMCQ;
            
            console.log('MCQ loaded:', currentDiagnosticMCQ); // Debug log
            displayDiagnosticMCQ(currentDiagnosticMCQ, questionIndex, diagnosticTotalQuestions);
        } else if (result && result.result && result.result.next_mode === 'complete') {
            // All questions answered
            handleDiagnosticComplete(result.result);
        } else {
            console.log('MCQ not available, using fallback'); // Debug log
            // Fallback to text input if MCQ not available
            showDiagnosticTextInput();
        }
        
        hideLoading();
    } catch (error) {
        console.error('Error loading diagnostic MCQ:', error); // Debug log
        hideLoading();
        showToast('Error loading diagnostic: ' + error.message, 'error');
        showDiagnosticTextInput(); // Fallback
    }
}

function displayDiagnosticMCQ(mcq, questionIndex, totalQuestions) {
    const diagnosticScreen = document.getElementById('diagnostic-screen');
    const questionCard = diagnosticScreen.querySelector('.question-card');
    
    if (!questionCard) {
        console.error('Question card not found in diagnostic screen');
        return;
    }
    
    if (!mcq || !mcq.question || !mcq.options) {
        console.error('Invalid MCQ data:', mcq);
        showDiagnosticTextInput();
        return;
    }
    
    const progressText = `Question ${questionIndex + 1} of ${totalQuestions}`;
    const progressPercent = ((questionIndex + 1) / totalQuestions) * 100;
    
    questionCard.innerHTML = `
        <div class="diagnostic-progress">
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progressPercent}%"></div>
            </div>
            <p class="progress-text">${progressText}</p>
        </div>
        <h3 id="diagnostic-question">${mcq.question}</h3>
        <div class="mcq-options" id="diagnostic-options">
            ${mcq.options.map((option, index) => `
                <button class="mcq-option" onclick="selectDiagnosticOption(${index})" data-option="${index}">
                    <span class="option-label">${String.fromCharCode(65 + index)})</span>
                    <span class="option-text">${option}</span>
                </button>
            `).join('')}
        </div>
        <button class="btn btn-primary" id="diagnostic-submit-btn" onclick="submitDiagnosticMCQ()" disabled>
            ${questionIndex < totalQuestions - 1 ? 'Next Question' : 'Complete Assessment'}
        </button>
    `;
    
    questionStartTime = Date.now(); // Reset timer when question is displayed
}

function showDiagnosticTextInput() {
    const diagnosticScreen = document.getElementById('diagnostic-screen');
    const questionCard = diagnosticScreen.querySelector('.question-card');
    
    if (questionCard) {
        questionCard.innerHTML = `
            <h3 id="diagnostic-question">In a sentence or two, what does AI do?</h3>
            <p class="hint">Not sure? Just type "skip"</p>
            <textarea id="diagnostic-answer" rows="4" placeholder="Your answer..." autofocus></textarea>
            <button class="btn btn-primary" onclick="submitDiagnostic()">Continue</button>
        `;
    }
}

function selectDiagnosticOption(optionIndex) {
    // Remove previous selection
    document.querySelectorAll('.mcq-option').forEach(opt => opt.classList.remove('selected'));
    
    // Mark selected option
    const selectedOption = document.querySelector(`[data-option="${optionIndex}"]`);
    if (selectedOption) {
        selectedOption.classList.add('selected');
        currentDiagnosticMCQ.selectedOption = optionIndex;
        document.getElementById('diagnostic-submit-btn').disabled = false;
    }
}

async function submitDiagnosticMCQ() {
    if (currentDiagnosticMCQ.selectedOption === undefined) {
        showToast('Please select an option', 'warning');
        return;
    }
    
    const hesitation = (Date.now() - questionStartTime) / 1000;
    const currentIndex = currentDiagnosticMCQ.questionIndex || diagnosticQuestionIndex;
    
    showLoading(currentIndex < diagnosticTotalQuestions - 1 ? 'Loading next question...' : 'Calculating your level...');
    
    try {
        const result = await apiCall('diagnostic', 'POST', {
            selected_option: currentDiagnosticMCQ.selectedOption,
            question_index: currentIndex,
            previous_answers: diagnosticPreviousAnswers,
            correct_answer_index: currentDiagnosticMCQ.correct_answer,  // Pass correct answer index
            hesitation_seconds: hesitation
        });
        
        if (result && result.result) {
            if (result.result.next_mode === 'complete') {
                // All questions answered
                handleDiagnosticComplete(result.result);
            } else if (result.result.next_mode === 'multiple_choice') {
                // Store current answer and load next question
                diagnosticPreviousAnswers.push({
                    question_index: currentIndex,
                    selected_option: currentDiagnosticMCQ.selectedOption,
                    hesitation_seconds: hesitation,
                    correct_answer_index: currentDiagnosticMCQ.correct_answer
                });
                
                diagnosticQuestionIndex = result.result.question_index || (currentIndex + 1);
                
                // Check cache first before using API result
                if (diagnosticQuestionCache[diagnosticQuestionIndex]) {
                    console.log(`Using cached question ${diagnosticQuestionIndex + 1} after submission`);
                    currentDiagnosticMCQ = diagnosticQuestionCache[diagnosticQuestionIndex];
                } else {
                    // Use API result and cache it
                    currentDiagnosticMCQ = result.result.question_payload;
                    currentDiagnosticMCQ.questionIndex = diagnosticQuestionIndex;
                    diagnosticQuestionCache[diagnosticQuestionIndex] = currentDiagnosticMCQ;
                }
                
                hideLoading();
                displayDiagnosticMCQ(currentDiagnosticMCQ, diagnosticQuestionIndex, diagnosticTotalQuestions);
            } else {
                // Fallback to lesson screen
                hideLoading();
                showScreen('lesson-screen');
                loadLesson();
            }
        } else {
            hideLoading();
            showScreen('lesson-screen');
            loadLesson();
        }
    } catch (error) {
        hideLoading();
        showToast('Error: ' + error.message, 'error');
    }
}

function handleDiagnosticComplete(result) {
    // Use nullish coalescing (??) instead of || to handle level 0 (Beginner) correctly
    // 0 is falsy in JavaScript, so || would default to 1 (Intermediate) when level is 0
    const assessedLevel = result.assessed_level ?? 1;
    const levelLabels = ['Beginner', 'Intermediate', 'Advanced', 'Expert'];
    const levelLabel = levelLabels[assessedLevel] ?? 'Intermediate';
    const allCorrect = result.all_correct || false;
    const allUnsure = result.all_unsure || false;
    const acceleratedModule = result.accelerated_module;
    const reasoning = result.reasoning || '';
    
    hideLoading();
    
    // Show appropriate message based on results
    let message = '';
    if (allCorrect && acceleratedModule) {
        message = `🎉 ${reasoning}`;
    } else if (allCorrect) {
        message = `Perfect score! Your level: ${levelLabel}`;
    } else if (allUnsure) {
        message = `No worries! We'll start from the basics. Your level: ${levelLabel}`;
    } else {
        message = `Assessment complete! Your level: ${levelLabel}`;
    }
    
    showToast(message, 'success', allCorrect ? 4000 : 3000);
    
    // Small delay before moving to lesson screen
    setTimeout(() => {
        showScreen('lesson-screen');
        loadLesson();
    }, allCorrect ? 2000 : 1500);
}

async function submitDiagnostic() {
    const answer = document.getElementById('diagnostic-answer').value.trim();
    if (!answer) {
        showToast('Please enter an answer', 'warning');
        return;
    }
    
    const hesitation = (Date.now() - questionStartTime) / 1000;
    
    showLoading('Analyzing your response...');
    
    try {
        const result = await apiCall('diagnostic', 'POST', {
            answer: answer,
            hesitation_seconds: hesitation
        });
        
        hideLoading();
        showScreen('lesson-screen');
        loadLesson();
    } catch (error) {
        hideLoading();
        showToast('Error: ' + error.message, 'error');
    }
}

// Lesson flow
async function loadLesson() {
    showLoading('Loading your personalized lesson...');
    
    try {
        const result = await apiCall('lesson');
        currentLesson = result.lesson;
        
        // Display lesson
        let moduleName = result.lesson.module.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        // Special case: show "Fundamentals of AI" instead of "Fundamentals"
        if (result.lesson.module === 'fundamentals') {
            moduleName = 'Fundamentals of AI';
        }
        // Handle clarification modules
        if (result.lesson.is_clarification) {
            moduleName = '📚 Clarification';
            // Add a badge or indicator that this is a clarification
            const moduleHeader = document.getElementById('lesson-module');
            moduleHeader.textContent = moduleName;
            moduleHeader.style.color = '#ff9800'; // Orange color for clarifications
        } else {
            document.getElementById('lesson-module').textContent = moduleName;
            document.getElementById('lesson-module').style.color = ''; // Reset color
        }
        
        const difficultyLabels = ['Beginner', 'Intermediate', 'Advanced', 'Expert'];
        const difficulty = result.lesson.difficulty || 1;
        document.getElementById('lesson-difficulty').textContent = 
            difficultyLabels[Math.min(difficulty, 3)];
        
        // Show page indicator if paginated
        if (result.lesson.is_paginated && result.lesson.total_pages > 1) {
            const pageInfo = document.createElement('div');
            pageInfo.className = 'lesson-page-info';
            pageInfo.innerHTML = `
                <span class="page-indicator">Page ${result.lesson.current_page + 1} of ${result.lesson.total_pages}</span>
            `;
            const lessonHeader = document.querySelector('.lesson-header');
            if (lessonHeader) {
                const existing = lessonHeader.querySelector('.lesson-page-info');
                if (existing) {
                    existing.remove();
                }
                lessonHeader.appendChild(pageInfo);
            }
            
            // Update button text
            const nextBtn = document.getElementById('next-lesson-btn');
            if (nextBtn) {
                const isLastPage = (result.lesson.current_page + 1) >= result.lesson.total_pages;
                nextBtn.textContent = isLastPage ? 'Next Module' : 'Next Page';
            }
        } else {
            // Remove page info if not paginated
            const pageInfo = document.querySelector('.lesson-page-info');
            if (pageInfo) {
                pageInfo.remove();
            }
            const nextBtn = document.getElementById('next-lesson-btn');
            if (nextBtn) {
                // If it's a clarification, show "Continue to Main Lesson"
                if (result.lesson.is_clarification) {
                    nextBtn.textContent = 'Continue to Main Lesson';
                    nextBtn.setAttribute('data-clarification-id', result.lesson.clarification_id || '');
                } else {
                    nextBtn.textContent = 'Next Lesson';
                    nextBtn.removeAttribute('data-clarification-id');
                }
            }
        }
        
        // Render markdown content
        const contentDiv = document.getElementById('lesson-content');
        let content = result.lesson.content || '';
        
        // Remove the first H1 heading if it matches "Fundamentals of AI - Page X" pattern
        // This removes redundant page titles since page info is already shown in the header
        if (content.trim().startsWith('# ')) {
            const firstLineEnd = content.indexOf('\n');
            if (firstLineEnd > 0) {
                const firstLine = content.substring(0, firstLineEnd);
                // Check if it's a page title pattern (e.g., "# Fundamentals of AI - Page 1")
                if (firstLine.match(/^#\s+.+-\s*Page\s+\d+/i)) {
                    // Remove the first line and any following blank lines
                    content = content.substring(firstLineEnd).trim();
                    // Remove leading blank lines
                    while (content.startsWith('\n')) {
                        content = content.substring(1);
                    }
                }
            }
        }
        
        if (window.marked) {
            contentDiv.innerHTML = marked.parse(content);
        } else {
            contentDiv.textContent = content;
        }
        
        // Load visual content (image or video) if available
        const imageContainer = document.getElementById('lesson-image-container');
        
        // Handle video reference if available
        if (result.lesson.video_reference) {
            // Display video description or embed
            const videoDiv = document.createElement('div');
            videoDiv.className = 'video-container';
            videoDiv.innerHTML = `
                <h4>📹 Video Resource</h4>
                <p class="video-description">${result.lesson.video_reference}</p>
            `;
            const lessonContent = document.getElementById('lesson-content');
            if (lessonContent) {
                lessonContent.appendChild(videoDiv);
            }
        }
        
        // Load image if available (only show if we have a valid, relevant image)
        if (result.lesson.image_reference) {
            if (result.lesson.image_reference.startsWith('http://') || result.lesson.image_reference.startsWith('https://')) {
                // Already a valid URL, display it directly
                const img = document.getElementById('lesson-image');
                const caption = document.getElementById('image-caption');
                
                // Set up error handling - hide if image fails to load
                img.onerror = function() {
                    console.log('Image failed to load, hiding container');
                    imageContainer.style.display = 'none';
                };
                img.onload = function() {
                    imageContainer.style.display = 'block';
                };
                
                img.src = result.lesson.image_reference;
                caption.textContent = `Visual aid for: ${result.lesson.module.replace(/_/g, ' ')}`;
            } else if (result.lesson.image_reference.startsWith('freepik://')) {
                // Extract search term from freepik:// URL
                const searchMatch = result.lesson.image_reference.match(/q=([^&]+)/);
                if (searchMatch) {
                    const searchTerm = decodeURIComponent(searchMatch[1].replace(/\+/g, ' '));
                    await loadFreepikImage(searchTerm);
                }
            } else if (result.lesson.image_reference.startsWith('gemini://')) {
                // Gemini-generated image reference
                const concept = result.lesson.image_reference.replace('gemini://', '').replace(/_/g, ' ');
                imageContainer.style.display = 'block';
                const caption = document.getElementById('image-caption');
                caption.textContent = `Visual aid: ${concept}`;
                // Note: Actual image URL would need to be fetched from Gemini API
            } else {
                // Treat as concept and fetch image
                await loadFreepikImage(result.lesson.image_reference);
            }
        } else {
            // No image available - hide the container
            imageContainer.style.display = 'none';
        }
        
        // Show check questions if available
        const checkQuestions = result.lesson.check_questions || [];
        if (checkQuestions.length > 0) {
            displayCheckQuestions(checkQuestions);
        }
        
        hideLoading();
    } catch (error) {
        hideLoading();
        showToast('Error loading lesson: ' + error.message, 'error');
    }
}

async function loadFreepikImage(concept) {
    try {
        const result = await apiCall(`freepik-image?concept=${encodeURIComponent(concept)}`);
        
        const container = document.getElementById('lesson-image-container');
        const img = document.getElementById('lesson-image');
        const caption = document.getElementById('image-caption');
        
        if (result.image_url && !result.image_url.startsWith('freepik://')) {
            // Set up image with error handling
            img.onerror = function() {
                console.error('Failed to load image:', result.image_url);
                container.style.display = 'none';
            };
            img.onload = function() {
                container.style.display = 'block';
            };
            img.src = result.image_url;
            caption.textContent = `Visual aid for: ${concept}`;
        } else {
            // If it's still a placeholder, hide the container
            container.style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading Freepik image:', error);
        document.getElementById('lesson-image-container').style.display = 'none';
    }
}

function displayCheckQuestions(questions) {
    const container = document.getElementById('check-questions-container');
    const list = document.getElementById('questions-list');
    list.innerHTML = '';
    
    questions.slice(0, 2).forEach((question, index) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-item';
        
        // Use global_index if available (for proper question_id tracking), otherwise use local index
        const globalIndex = question.global_index !== undefined ? question.global_index : index;
        const questionId = `${currentLesson.module}_q${globalIndex}`;
        
        // Check if it's an MCQ (has options) or text question
        if (question.options && Array.isArray(question.options)) {
            // MCQ format
            questionDiv.innerHTML = `
                <h4>Question ${index + 1}: ${question.question}</h4>
                <div class="mcq-options" id="options-${index}">
                    ${question.options.map((option, optIndex) => `
                        <button class="mcq-option" onclick="selectCheckQuestionOption(${index}, ${optIndex})" data-question="${index}" data-option="${optIndex}">
                            <span class="option-label">${String.fromCharCode(65 + optIndex)})</span>
                            <span class="option-text">${option}</span>
                        </button>
                    `).join('')}
                </div>
                <button class="btn btn-primary" id="submit-btn-${index}" onclick="submitMCQAnswer(${index}, '${questionId}', ${question.correct_answer || 0}, '${(question.question || '').replace(/'/g, "\\'")}')" disabled>Submit Answer</button>
                <div id="feedback-${index}" class="feedback" style="display: none;"></div>
            `;
        } else {
            // Text question format (open-ended questions)
            const questionText = typeof question === 'string' ? question : question.question || question;
            const escapedQuestionText = questionText.replace(/'/g, "\\'");
            questionDiv.innerHTML = `
                <h4>Question ${index + 1}: ${questionText}</h4>
                <textarea id="answer-${index}" rows="3" placeholder="Your answer..."></textarea>
                <button class="btn btn-primary" onclick="submitAnswer(${index}, '${questionId}', '${escapedQuestionText}')">Submit Answer</button>
                <div id="feedback-${index}" class="feedback" style="display: none;"></div>
            `;
        }
        
        list.appendChild(questionDiv);
    });
    
    container.style.display = 'block';
}

function selectCheckQuestionOption(questionIndex, optionIndex) {
    // Remove previous selection for this question
    document.querySelectorAll(`[data-question="${questionIndex}"].mcq-option`).forEach(opt => opt.classList.remove('selected'));
    
    // Mark selected option
    const selectedOption = document.querySelector(`[data-question="${questionIndex}"][data-option="${optionIndex}"]`);
    if (selectedOption) {
        selectedOption.classList.add('selected');
        document.getElementById(`submit-btn-${questionIndex}`).disabled = false;
    }
}

async function submitMCQAnswer(questionIndex, questionId, correctAnswerIndex, questionText = '') {
    // Prevent multiple submissions
    const submitBtn = document.getElementById(`submit-btn-${questionIndex}`);
    if (submitBtn && submitBtn.disabled) {
        return; // Already submitted
    }
    
    const selectedOption = document.querySelector(`[data-question="${questionIndex}"].mcq-option.selected`);
    if (!selectedOption) {
        showToast('Please select an option', 'warning');
        return;
    }
    
    const selectedIndex = parseInt(selectedOption.getAttribute('data-option'));
    const startTime = Date.now();
    const hesitation = (Date.now() - startTime) / 1000;
    
    // Disable button immediately to prevent double-clicks
    if (submitBtn) {
        submitBtn.disabled = true;
    }
    
    showLoading('Checking your answer...');
    
    try {
        const result = await apiCall('quiz', 'POST', {
            question_id: questionId,
            question: questionText,  // Pass question text for clarification generation
            selected_option: selectedIndex,
            correct_answer_index: correctAnswerIndex,
            hesitation_seconds: hesitation
        });
        
        hideLoading();
        
        const feedbackDiv = document.getElementById(`feedback-${questionIndex}`);
        const feedback = result.feedback;
        
        if (feedback.is_correct) {
            feedbackDiv.className = 'feedback correct';
            feedbackDiv.innerHTML = '✅ Correct! Great job!';
        } else {
            feedbackDiv.className = 'feedback incorrect';
            const correctLabel = String.fromCharCode(65 + correctAnswerIndex);
            feedbackDiv.innerHTML = `❌ Not quite right. The correct answer is ${correctLabel}.`;
        }
        
        feedbackDiv.style.display = 'block';
        
        // Disable all options after submission
        document.querySelectorAll(`[data-question="${questionIndex}"].mcq-option`).forEach(opt => {
            opt.disabled = true;
            if (parseInt(opt.getAttribute('data-option')) === correctAnswerIndex) {
                opt.classList.add('correct-answer');
            }
        });
        document.getElementById(`submit-btn-${questionIndex}`).disabled = true;
        
        if (feedback.difficulty_changed) {
            setTimeout(() => {
                showToast(`I've ${feedback.change_direction} the difficulty to match your pace.`, 'info', 4000);
            }, 500);
        }
        
        // Update dashboard if it's open
        const dashboard = document.getElementById('learning-dashboard');
        if (dashboard && dashboard.style.display !== 'none') {
            setTimeout(updateLearningDashboard, 500);
        }
    } catch (error) {
        hideLoading();
        showToast('Error submitting answer: ' + error.message, 'error');
        // Re-enable button on error so user can retry
        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }
}

async function submitAnswer(questionIndex, questionId, questionText = '') {
    const answerInput = document.getElementById(`answer-${questionIndex}`);
    const answer = answerInput.value.trim();
    
    if (!answer) {
        showToast('Please enter an answer', 'warning');
        return;
    }
    
    // Prevent multiple submissions
    if (answerInput.disabled) {
        return; // Already submitted
    }
    
    const startTime = Date.now();
    const hesitation = (Date.now() - startTime) / 1000;
    
    // Disable input immediately to prevent double-submissions
    answerInput.disabled = true;
    
    showLoading('Checking your answer...');
    
    try {
        const result = await apiCall('quiz', 'POST', {
            question_id: questionId,
            question: questionText,  // Pass question text for semantic evaluation
            answer: answer,
            correct_answer: '',  // Not needed for semantic evaluation
            hesitation_seconds: hesitation
        });
        
        hideLoading();
        
        const feedbackDiv = document.getElementById(`feedback-${questionIndex}`);
        const feedback = result.feedback;
        
        // Use is_correct for consistency (works for both MCQ and open-ended)
        const isCorrect = feedback.is_correct !== undefined ? feedback.is_correct : feedback.correct;
        
        if (isCorrect) {
            feedbackDiv.className = 'feedback correct';
            feedbackDiv.textContent = '✅ Correct! Great job!';
            // Show reasoning if available for open-ended questions
            if (feedback.reasoning) {
                feedbackDiv.innerHTML = '✅ <strong>Correct!</strong> ' + feedback.reasoning;
            }
        } else {
            feedbackDiv.className = 'feedback incorrect';
            feedbackDiv.textContent = '❌ Not quite right. Let\'s keep learning!';
            // Show reasoning if available
            if (feedback.reasoning) {
                feedbackDiv.innerHTML = '❌ <strong>Not quite right.</strong> ' + feedback.reasoning;
            }
        }
        
        feedbackDiv.style.display = 'block';
        
        // Disable the textarea and button after submission
        answerInput.disabled = true;
        const submitButton = answerInput.parentElement.querySelector('button');
        if (submitButton) {
            submitButton.disabled = true;
        }
        
        if (feedback.difficulty_changed) {
            setTimeout(() => {
                showToast(`I've ${feedback.change_direction} the difficulty to match your pace.`, 'info', 4000);
            }, 500);
        }
        
        if (feedback.should_switch_to_examples) {
            setTimeout(() => {
                showToast('I\'ll focus more on examples in the next lesson.', 'info', 4000);
            }, 500);
        }
        
        // Update dashboard if it's open
        const dashboard = document.getElementById('learning-dashboard');
        if (dashboard && dashboard.style.display !== 'none') {
            setTimeout(updateLearningDashboard, 500);
        }
    } catch (error) {
        hideLoading();
        showToast('Error submitting answer: ' + error.message, 'error');
        // Re-enable input on error so user can retry
        answerInput.disabled = false;
        const submitButton = answerInput.parentElement.querySelector('button');
        if (submitButton) {
            submitButton.disabled = false;
        }
    }
}

async function nextLesson() {
    showLoading('Loading next page...');
    
    try {
        // Check if current lesson is a clarification and complete it first
        const nextBtn = document.getElementById('next-lesson-btn');
        const clarificationId = nextBtn?.getAttribute('data-clarification-id') || 
                                (currentLesson && currentLesson.clarification_id);
        
        let justCompletedClarification = false;
        if (clarificationId && currentLesson && currentLesson.is_clarification) {
            try {
                await apiCall('clarification/complete', 'POST', {
                    clarification_id: clarificationId
                });
                showToast('Clarification completed. Returning to main lesson...', 'success', 2000);
                // Small delay to show the toast before loading next lesson
                await new Promise(resolve => setTimeout(resolve, 500));
                justCompletedClarification = true;
            } catch (error) {
                console.error('Error completing clarification:', error);
                // Continue anyway - don't block the user from proceeding
                showToast('Note: Could not mark clarification as complete, but continuing...', 'warning', 2000);
                justCompletedClarification = true; // Still proceed as if completed
            }
        }
        
        // If we just completed a clarification, just load the next lesson directly
        // (don't advance module since we're not in a real module)
        if (justCompletedClarification) {
            await loadLesson();
            return;
        }
        
        // Check if current lesson is paginated
        if (currentLesson && currentLesson.is_paginated) {
            // Advance to next page within module
            const result = await apiCall('lesson/next-page', 'POST');
            
            // Check if next modules are coming soon
            if (result.coming_soon) {
                hideLoading();
                showComingSoonMessage(result.message || 'AI Agents and Capstone modules are coming soon!');
                return;
            }
            
            if (result.has_more_pages) {
                await loadLesson();
                showToast(`Page ${result.lesson.current_page + 1} of ${result.lesson.total_pages}`, 'info', 2000);
            } else if (result.module_advanced) {
                showToast('Moving to next module!', 'success', 2000);
                await loadLesson();
            } else {
                showToast('All modules completed!', 'success', 3000);
            }
        } else {
            // Not paginated, advance to next module
            const result = await apiCall('advance', 'POST');
            
            // Check if next modules are coming soon
            if (result.coming_soon) {
                hideLoading();
                showComingSoonMessage(result.message || 'AI Agents and Capstone modules are coming soon!');
                return;
            }
            
            await loadLesson();
        }
    } catch (error) {
        hideLoading();
        showToast('Error advancing: ' + error.message, 'error');
    }
}

// Capstone flow
function showCapstone() {
    showScreen('capstone-screen');
}

async function generateCapstone() {
    const description = document.getElementById('capstone-description').value.trim();
    
    if (!description) {
        showToast('Please describe what you want your agent to do', 'warning');
        return;
    }
    
    showLoading('Generating your custom AI agent...');
    
    try {
        const result = await apiCall('capstone', 'POST', {
            task_description: description
        });
        
        hideLoading();
        
        const resultDiv = document.getElementById('capstone-result');
        const descText = document.getElementById('capstone-description-text');
        const codeElement = document.getElementById('capstone-code');
        const nextStepsDiv = document.getElementById('capstone-next-steps');
        
        descText.textContent = result.result.agent_description || 'Your custom agent';
        
        const code = result.result.agent_code || '';
        codeElement.textContent = code;
        
        // Highlight code
        if (window.hljs) {
            hljs.highlightElement(codeElement);
        }
        
        // Show next steps
        const nextSteps = result.result.next_steps || [];
        if (nextSteps.length > 0) {
            nextStepsDiv.innerHTML = '<h3>Next Steps:</h3><ul>';
            nextSteps.forEach(step => {
                nextStepsDiv.innerHTML += `<li>${step}</li>`;
            });
            nextStepsDiv.innerHTML += '</ul>';
        }
        
        resultDiv.style.display = 'block';
        
        // Store code for download
        window.capstoneCode = code;
    } catch (error) {
        hideLoading();
        showToast('Error generating capstone: ' + error.message, 'error');
    }
}

function downloadCode() {
    if (!window.capstoneCode) {
        showToast('No code to download', 'warning');
        return;
    }
    
    const blob = new Blob([window.capstoneCode], { type: 'text/python' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'my_agent.py';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Progress flow
async function showProgress() {
    showLoading('Loading your progress...');
    
    try {
        const result = await apiCall('progress');
        const statsDiv = document.getElementById('progress-stats');
        
        const progress = result.progress;
        statsDiv.innerHTML = `
            <div class="stat-card">
                <h3>${progress.current_module || 'N/A'}</h3>
                <p>Current Module</p>
            </div>
            <div class="stat-card">
                <h3>${progress.difficulty_level || 1}/3</h3>
                <p>Difficulty Level</p>
            </div>
            <div class="stat-card">
                <h3>${(progress.completed_modules || []).length}</h3>
                <p>Completed Modules</p>
            </div>
            <div class="stat-card">
                <h3>${progress.total_questions || 0}</h3>
                <p>Questions Answered</p>
            </div>
            ${progress.total_questions > 0 ? `
            <div class="stat-card">
                <h3>${((progress.accuracy || 0) * 100).toFixed(1)}%</h3>
                <p>Accuracy</p>
            </div>
            ` : ''}
        `;
        
        hideLoading();
        showScreen('progress-screen');
    } catch (error) {
        hideLoading();
        showToast('Error loading progress: ' + error.message, 'error');
    }
}

function showComingSoonMessage(message) {
    // Create a modal-like overlay to show the coming soon message
    const overlay = document.createElement('div');
    overlay.className = 'coming-soon-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    `;
    
    const modal = document.createElement('div');
    modal.className = 'coming-soon-modal';
    modal.style.cssText = `
        background: var(--surface-color, #1a1a2e);
        padding: 3rem;
        border-radius: 16px;
        max-width: 500px;
        text-align: center;
        border: 2px solid var(--primary-color, #3b82f6);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        animation: slideUp 0.3s ease;
    `;
    
    modal.innerHTML = `
        <h2 style="color: var(--primary-color, #3b82f6); margin-bottom: 1rem; font-size: 2rem;">🎉 Congratulations!</h2>
        <p style="color: var(--text-color, #e0e0e0); font-size: 1.1rem; line-height: 1.6; margin-bottom: 2rem;">${message}</p>
        <p style="color: var(--text-secondary, #a0a0a0); font-size: 0.9rem; margin-bottom: 2rem;">You've completed the available modules. Check back soon for new content!</p>
        <button class="btn btn-primary" onclick="this.closest('.coming-soon-overlay').remove(); showScreen('welcome-screen');" style="padding: 0.75rem 2rem; font-size: 1rem;">Return to Home</button>
    `;
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    
    // Add animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
    `;
    if (!document.querySelector('style[data-coming-soon]')) {
        style.setAttribute('data-coming-soon', 'true');
        document.head.appendChild(style);
    }
}

function goBack() {
    if (currentScreen === 'progress-screen') {
        showScreen('lesson-screen');
    } else {
        showScreen('welcome-screen');
    }
}

async function resetProgress() {
    if (!confirm('Are you sure you want to reset your progress? This cannot be undone.')) {
        return;
    }
    
    showLoading('Resetting progress...');
    
    try {
        await apiCall('reset', 'POST');
        hideLoading();
        showToast('Progress reset successfully!', 'success');
        showScreen('welcome-screen');
    } catch (error) {
        hideLoading();
        showToast('Error resetting progress: ' + error.message, 'error');
    }
}

// Learning Dashboard Functions
let dashboardUpdateInterval = null;

function toggleLearningDashboard() {
    const dashboard = document.getElementById('learning-dashboard');
    if (dashboard.style.display === 'none') {
        dashboard.style.display = 'block';
        updateLearningDashboard();
        // Auto-refresh every 10 seconds when dashboard is open (reduced from 2s to feel less rushed)
        dashboardUpdateInterval = setInterval(updateLearningDashboard, 10000);
    } else {
        dashboard.style.display = 'none';
        if (dashboardUpdateInterval) {
            clearInterval(dashboardUpdateInterval);
            dashboardUpdateInterval = null;
        }
    }
}

async function updateLearningDashboard() {
    try {
        const result = await apiCall('learning-insights');
        const insights = result.insights;
        
        // Update current state
        const difficultyLabels = ['Beginner', 'Intermediate', 'Advanced', 'Expert'];
        document.getElementById('dashboard-difficulty').textContent = 
            difficultyLabels[Math.min(insights.current_difficulty || 0, 3)];
        
        const styleLabels = {
            'text': 'Text-based',
            'visual': 'Visual',
            'examples': 'Examples-first'
        };
        document.getElementById('dashboard-style').textContent = 
            styleLabels[insights.learning_style] || 'Text-based';
        
        document.getElementById('dashboard-total').textContent = 
            insights.performance_metrics.total_attempts || 0;
        
        // Update performance metrics
        const accuracy = (insights.performance_metrics.recent_accuracy * 100).toFixed(1);
        document.getElementById('dashboard-accuracy').textContent = 
            insights.performance_metrics.recent_accuracy > 0 ? `${accuracy}%` : 'N/A';
        
        const hesitation = insights.performance_metrics.avg_hesitation.toFixed(1);
        document.getElementById('dashboard-hesitation').textContent = 
            insights.performance_metrics.avg_hesitation > 0 ? `${hesitation}s` : 'N/A';
        
        const trendLabels = {
            'increasing': '📈 Increasing',
            'decreasing': '📉 Decreasing',
            'stable': '➡️ Stable'
        };
        document.getElementById('dashboard-trend').textContent = 
            trendLabels[insights.performance_metrics.difficulty_trend] || '➡️ Stable';
        
        // Update AI insights
        const insightsContainer = document.getElementById('dashboard-insights');
        if (insights.ai_insights && insights.ai_insights.length > 0) {
            insightsContainer.innerHTML = insights.ai_insights.map(insight => `
                <div class="insight-item ${insight.type}">
                    <span class="insight-icon">${insight.icon}</span>
                    <p class="insight-message">${insight.message}</p>
                </div>
            `).join('');
        } else {
            insightsContainer.innerHTML = '<p class="no-insights">No insights yet. Start learning to see how the AI adapts!</p>';
        }
        
        // Update adaptation history
        const adaptationsContainer = document.getElementById('dashboard-adaptations');
        if (insights.adaptations && insights.adaptations.length > 0) {
            adaptationsContainer.innerHTML = insights.adaptations.reverse().map(adaptation => {
                const time = new Date(adaptation.timestamp).toLocaleTimeString();
                return `
                    <div class="adaptation-item ${adaptation.direction}">
                        <div class="adaptation-header">
                            <span class="adaptation-type">Difficulty ${adaptation.direction}</span>
                            <span class="adaptation-time">${time}</span>
                        </div>
                        <div class="adaptation-details">
                            Changed from level ${adaptation.from} to ${adaptation.to}. ${adaptation.reason}
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            adaptationsContainer.innerHTML = '<p class="no-adaptations">No adaptations yet. The AI will adjust as you learn!</p>';
        }
        
        // Update performance chart
        updatePerformanceChart(insights.quiz_history, insights.hesitation_history);
        
    } catch (error) {
        console.error('Error updating learning dashboard:', error);
    }
}

function updatePerformanceChart(quizHistory, hesitationHistory) {
    const chartContainer = document.getElementById('simple-chart');
    
    if (!quizHistory || quizHistory.length === 0) {
        chartContainer.innerHTML = '<p style="color: var(--text-secondary);">Chart will appear as you answer questions</p>';
        return;
    }
    
    // Create a simple bar chart showing accuracy over time
    const maxValue = 100; // 100% accuracy
    const bars = quizHistory.map((attempt, index) => {
        const accuracy = attempt.correct ? 100 : 0;
        const height = (accuracy / maxValue) * 100;
        const hesitation = hesitationHistory[index] || 0;
        
        return `
            <div class="chart-bar" 
                 style="height: ${height}%;" 
                 data-value="${accuracy}%"
                 title="Question ${index + 1}: ${attempt.correct ? 'Correct' : 'Incorrect'} (${hesitation.toFixed(1)}s)">
            </div>
        `;
    }).join('');
    
    chartContainer.innerHTML = bars;
}

// Admin Dashboard Functions
let adminKey = null;
let adminUpdateInterval = null;

function showAdminLogin() {
    document.getElementById('admin-login-modal').style.display = 'flex';
    document.getElementById('admin-key-input').focus();
}

function closeAdminLogin() {
    document.getElementById('admin-login-modal').style.display = 'none';
    document.getElementById('admin-key-input').value = '';
}

function authenticateAdmin() {
    const key = document.getElementById('admin-key-input').value;
    if (!key) {
        showToast('Please enter an admin key', 'warning');
        return;
    }
    
    adminKey = key;
    closeAdminLogin();
    toggleAdminDashboard();
}

function toggleAdminDashboard() {
    const dashboard = document.getElementById('admin-dashboard');
    if (dashboard.style.display === 'none') {
        if (!adminKey) {
            showAdminLogin();
            return;
        }
        dashboard.style.display = 'block';
        updateAdminDashboard();
        // Auto-refresh every 5 seconds when dashboard is open
        adminUpdateInterval = setInterval(updateAdminDashboard, 5000);
    } else {
        dashboard.style.display = 'none';
        if (adminUpdateInterval) {
            clearInterval(adminUpdateInterval);
            adminUpdateInterval = null;
        }
    }
}

async function updateAdminDashboard() {
    if (!adminKey) return;
    
    try {
        // Use fetch directly for query parameters
        const response = await fetch(`/api/admin/dashboard?key=${encodeURIComponent(adminKey)}`);
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Failed to load admin dashboard');
        }
        
        const data = result.dashboard;
        
        // Update system statistics
        document.getElementById('admin-total-users').textContent = data.system_stats.total_users;
        document.getElementById('admin-total-questions').textContent = data.system_stats.total_questions;
        document.getElementById('admin-total-lessons').textContent = data.system_stats.total_lessons_viewed;
        document.getElementById('admin-system-accuracy').textContent = 
            (data.system_stats.system_accuracy * 100).toFixed(1) + '%';
        document.getElementById('admin-avg-hesitation').textContent = 
            data.system_stats.avg_hesitation_seconds.toFixed(1) + 's';
        
        // Update difficulty distribution
        renderDistributionChart('difficulty-chart', data.difficulty_distribution, 
            ['Beginner', 'Intermediate', 'Advanced', 'Expert']);
        
        // Update style distribution
        renderDistributionChart('style-chart', data.style_distribution, null);
        
        // Update module completion
        renderDistributionChart('module-chart', data.module_stats, null);
        
        // Update users table
        renderUsersTable(data.users);
        
        // Update recent activity
        renderRecentActivity(data.recent_activity);
        
        // Update technology stack usage
        renderLiquidMetalStats(data.liquidmetal_stats);
        renderDaftStats(data.daft_stats);
        renderFastinoStats(data.fastino_stats);
        
    } catch (error) {
        console.error('Error updating admin dashboard:', error);
        if (error.message.includes('Unauthorized')) {
            adminKey = null;
            toggleAdminDashboard();
            showToast('Admin key expired or invalid. Please re-authenticate.', 'error');
        }
    }
}

function renderDistributionChart(containerId, data, labels) {
    const container = document.getElementById(containerId);
    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<p class="no-activity">No data available</p>';
        return;
    }
    
    const total = Object.values(data).reduce((sum, val) => sum + val, 0);
    if (total === 0) {
        container.innerHTML = '<p class="no-activity">No data available</p>';
        return;
    }
    
    const items = Object.entries(data).map(([key, value], index) => {
        const percentage = (value / total * 100).toFixed(1);
        const label = labels ? labels[index] || key : key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        
        return `
            <div class="dist-item">
                <div>
                    <div class="dist-label">${label}</div>
                    <div class="dist-bar" style="width: ${percentage}%"></div>
                </div>
                <div class="dist-value">${value} (${percentage}%)</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = items;
}

function renderUsersTable(users) {
    const tbody = document.getElementById('admin-users-table');
    
    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8">No users found</td></tr>';
        return;
    }
    
    const difficultyLabels = ['Beginner', 'Intermediate', 'Advanced', 'Expert'];
    const styleLabels = {
        'text': 'Text',
        'visual': 'Visual',
        'examples': 'Examples'
    };
    
    tbody.innerHTML = users.map(user => {
        const lastActive = user.last_active ? new Date(user.last_active).toLocaleString() : 'N/A';
        const accuracy = (user.accuracy * 100).toFixed(1);
        
        return `
            <tr>
                <td>${user.user_id}</td>
                <td>${user.current_module.replace(/_/g, ' ')}</td>
                <td>${difficultyLabels[Math.min(user.difficulty_level || 0, 3)]}</td>
                <td>${user.completed_modules}</td>
                <td>${user.total_questions}</td>
                <td>${user.total_questions > 0 ? accuracy + '%' : 'N/A'}</td>
                <td>${styleLabels[user.learning_style] || 'Text'}</td>
                <td>${lastActive}</td>
            </tr>
        `;
    }).join('');
}

function renderRecentActivity(activities) {
    const container = document.getElementById('admin-recent-activity');
    
    if (!activities || activities.length === 0) {
        container.innerHTML = '<p class="no-activity">No recent activity</p>';
        return;
    }
    
    container.innerHTML = activities.map(activity => {
        const timestamp = activity.timestamp;
        let timeStr = 'Unknown';
        try {
            if (typeof timestamp === 'number') {
                timeStr = new Date(timestamp * 1000).toLocaleString();
            } else {
                timeStr = new Date(timestamp).toLocaleString();
            }
        } catch (e) {
            timeStr = 'Unknown';
        }
        
        const correct = activity.correct ? '✅' : '❌';
        const questionId = activity.question_id || 'Unknown';
        const hesitation = activity.hesitation_seconds ? activity.hesitation_seconds.toFixed(1) + 's' : 'N/A';
        
        return `
            <div class="activity-item">
                <div class="activity-header">
                    <span class="activity-user">${activity.user_id}</span>
                    <span class="activity-time">${timeStr}</span>
                </div>
                <div class="activity-details">
                    ${correct} ${questionId} (${hesitation})
                </div>
            </div>
        `;
    }).join('');
}

function renderLiquidMetalStats(liquidmetalStats) {
    const container = document.getElementById('liquidmetal-stats-container');
    
    if (!liquidmetalStats || !liquidmetalStats.available) {
        container.innerHTML = `
            <div class="tech-status disabled">
                <p><strong>Status:</strong> <span style="color: #ef4444;">Not Available</span></p>
                <p class="tech-hint">Install with: pip install lm-raindrop</p>
            </div>
        `;
        return;
    }
    
    const usage = liquidmetalStats.usage || {};
    const lastUsed = usage.last_used ? new Date(usage.last_used).toLocaleString() : 'Never';
    const successRate = usage.total_agent_calls > 0 
        ? ((usage.successful_calls / usage.total_agent_calls) * 100).toFixed(1) 
        : '0';
    
    container.innerHTML = `
        <div class="tech-status enabled">
            <p><strong>Status:</strong> <span style="color: #10b981;">✅ Available</span></p>
            <div class="tech-metrics">
                <div class="tech-metric">
                    <span class="metric-label">📞 Total Agent Calls:</span>
                    <span class="metric-value">${usage.total_agent_calls || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">✅ Successful:</span>
                    <span class="metric-value">${usage.successful_calls || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">❌ Failed:</span>
                    <span class="metric-value">${usage.failed_calls || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">📊 Success Rate:</span>
                    <span class="metric-value">${successRate}%</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">🔍 Diagnostic Calls:</span>
                    <span class="metric-value">${usage.diagnostic_calls || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">📚 Lesson Calls:</span>
                    <span class="metric-value">${usage.lesson_calls || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">🎓 Capstone Calls:</span>
                    <span class="metric-value">${usage.capstone_calls || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">🔄 OpenAI Fallbacks:</span>
                    <span class="metric-value">${usage.fallback_to_openai || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">⚙️ Heuristic Fallbacks:</span>
                    <span class="metric-value">${usage.fallback_to_heuristics || 0}</span>
                </div>
            </div>
            <p class="tech-last-used"><strong>Last Used:</strong> ${lastUsed}</p>
        </div>
    `;
}

function renderDaftStats(daftStats) {
    const container = document.getElementById('daft-stats-container');
    
    if (!daftStats || !daftStats.available) {
        container.innerHTML = `
            <div class="tech-status disabled">
                <p><strong>Status:</strong> <span style="color: #ef4444;">Not Available</span></p>
                <p class="tech-hint">Using JSON fallback storage</p>
            </div>
        `;
        return;
    }
    
    const usage = daftStats.usage || {};
    const lastUsed = usage.last_used ? new Date(usage.last_used).toLocaleString() : 'Never';
    const storageMode = usage.using_daft ? 'Parquet (Daft)' : 'JSON (Fallback)';
    
    container.innerHTML = `
        <div class="tech-status enabled">
            <p><strong>Status:</strong> <span style="color: #10b981;">✅ Available</span></p>
            <p><strong>Storage Mode:</strong> ${storageMode}</p>
            <div class="tech-metrics">
                <div class="tech-metric">
                    <span class="metric-label">📥 Parquet Writes:</span>
                    <span class="metric-value">${usage.parquet_writes || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">📤 Parquet Reads:</span>
                    <span class="metric-value">${usage.parquet_reads || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">📝 JSON Writes:</span>
                    <span class="metric-value">${usage.json_writes || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">📖 JSON Reads:</span>
                    <span class="metric-value">${usage.json_reads || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">❓ Quiz Attempts Logged:</span>
                    <span class="metric-value">${usage.quiz_attempts_logged || 0}</span>
                </div>
                <div class="tech-metric">
                    <span class="metric-label">📚 Lesson Events Logged:</span>
                    <span class="metric-value">${usage.lesson_events_logged || 0}</span>
                </div>
            </div>
            <p class="tech-last-used"><strong>Last Used:</strong> ${lastUsed}</p>
        </div>
    `;
}

function renderFastinoStats(fastinoStats) {
    const container = document.getElementById('fastino-stats-container');
    
    if (!fastinoStats || !fastinoStats.enabled) {
        container.innerHTML = `
            <div class="fastino-status disabled">
                <p><strong>Status:</strong> <span style="color: #ef4444;">Not Enabled</span></p>
                <p class="fastino-hint">Add FASTINO_API_KEY to .env to enable enhanced personalization</p>
            </div>
        `;
        return;
    }
    
    const usage = fastinoStats.usage || {};
    const lastUsed = usage.last_used ? new Date(usage.last_used).toLocaleString() : 'Never';
    
    container.innerHTML = `
        <div class="fastino-status enabled">
            <p><strong>Status:</strong> <span style="color: #10b981;">✅ Enabled</span></p>
            <div class="fastino-metrics">
                <div class="fastino-metric">
                    <span class="metric-label">👤 Users Registered:</span>
                    <span class="metric-value">${usage.users_registered || 0}</span>
                </div>
                <div class="fastino-metric">
                    <span class="metric-label">📥 Events Ingested:</span>
                    <span class="metric-value">${usage.events_ingested || 0}</span>
                </div>
                <div class="fastino-metric">
                    <span class="metric-label">🔍 Profile Queries:</span>
                    <span class="metric-value">${usage.queries_made || 0}</span>
                </div>
                <div class="fastino-metric">
                    <span class="metric-label">🧠 RAG Retrievals:</span>
                    <span class="metric-value">${usage.retrievals_made || 0}</span>
                </div>
                <div class="fastino-metric">
                    <span class="metric-label">📊 Summaries Fetched:</span>
                    <span class="metric-value">${usage.summaries_fetched || 0}</span>
                </div>
                <div class="fastino-metric">
                    <span class="metric-label">🔮 Predictions Made:</span>
                    <span class="metric-value">${usage.predictions_made || 0}</span>
                </div>
            </div>
            <p class="fastino-last-used"><strong>Last Used:</strong> ${lastUsed}</p>
            <div class="fastino-tools">
                <h4>Fastino Tools in Use:</h4>
                <ul class="fastino-tools-list">
                    <li>✅ <strong>User Memory:</strong> Persistent user profiles across sessions</li>
                    <li>✅ <strong>Event Ingestion:</strong> Learning activities logged to memory</li>
                    <li>✅ <strong>RAG Retrieval:</strong> Personalized context for lessons</li>
                    <li>✅ <strong>Profile Querying:</strong> Learning style recommendations</li>
                    <li>${usage.summaries_fetched > 0 ? '✅' : '⏸️'} <strong>Summaries:</strong> User progress summaries</li>
                    <li>${usage.predictions_made > 0 ? '✅' : '⏸️'} <strong>Decision Prediction:</strong> Learning path recommendations</li>
                </ul>
            </div>
        </div>
    `;
}

// Theme Toggle
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
    updateHighlightTheme(newTheme);
}

function updateHighlightTheme(theme) {
    const link = document.querySelector('link[href*="highlight.js"]');
    if (link) {
        const newHref = theme === 'light' 
            ? 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css'
            : 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css';
        link.href = newHref;
    }
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('theme-icon');
    const text = document.getElementById('theme-text');
    
    if (icon && text) {
        if (theme === 'light') {
            icon.textContent = '🌙';
            text.textContent = 'Dark Mode';
        } else {
            icon.textContent = '☀️';
            text.textContent = 'Light Mode';
        }
    }
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    const html = document.documentElement;
    html.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
    updateHighlightTheme(savedTheme);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    showScreen('welcome-screen');
    
    // Allow Enter key in admin login
    const adminInput = document.getElementById('admin-key-input');
    if (adminInput) {
        adminInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                authenticateAdmin();
            }
        });
    }
});

