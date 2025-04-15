document.addEventListener('DOMContentLoaded', function() {
    // Initialize CodeMirror
    const codeEditorTextarea = document.getElementById('code-editor');
    const codeEditor = CodeMirror.fromTextArea(codeEditorTextarea, {
        mode: 'python',
        theme: 'monokai',
        lineNumbers: true,
        indentUnit: 4,
        smartIndent: true,
        indentWithTabs: false,
        electricChars: true,
        matchBrackets: true,
        autoCloseBrackets: true,
        extraKeys: {
            "Tab": function(cm) {
                // Insert spaces instead of tab character
                const spaces = Array(cm.getOption("indentUnit") + 1).join(" ");
                cm.replaceSelection(spaces);
            }
        },
        lineWrapping: true,
        autofocus: true
    });
    
    const analyzeBtn = document.getElementById('analyze-btn');
    const resultsDiv = document.getElementById('results');
    const loadingDiv = document.getElementById('loading');

    // Add event listener to the analyze button
    analyzeBtn.addEventListener('click', () => {
        const code = codeEditor.getValue().trim();
        
        // Check if code is empty
        if (!code) {
            showMessage('Please enter some Python code to analyze for runtime issues.');
            return;
        }
        
        // Show loading indicator
        loadingDiv.classList.remove('hidden');
        resultsDiv.innerHTML = '';
        
        // Send code to the backend for analysis
        analyzeCode(code);
    });

    // Function to send code to the backend
    async function analyzeCode(code) {
        try {
            console.log('Sending code to backend for analysis...');
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ code })
            });
            
            if (!response.ok) {
                console.error(`HTTP error! Status: ${response.status}`);
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Received analysis results:', data);
            console.log('Number of feedback items:', data.feedback.length);
            
            // Check if any items have explanations
            const hasExplanations = data.feedback.some(item => item.explanation);
            console.log('Has explanations from Claude:', hasExplanations);
            
            if (!hasExplanations && data.feedback.length > 0) {
                console.warn('No explanations found in the feedback items. Claude API may not be working.');
                data.feedback.forEach((item, index) => {
                    console.log(`Item ${index + 1}:`, item);
                });
                
                // Add a system message about Claude API not working
                data.feedback.push({
                    line: 0,
                    message: 'Claude API is not providing explanations. Please check the environment variables in Vercel.',
                    category: 'syntax_error',
                    source: 'system',
                    explanation: null,
                    fix: null
                });
            }
            
            // If no feedback items at all, add a test item to verify the analyzer is working
            if (data.feedback.length === 0) {
                data.feedback.push({
                    line: 1,
                    message: 'Your code is fine.',
                    category: '',
                    source: '',
                    explanation: null,
                    fix: null
                });
            }
            
            displayResults(data.feedback);
        } catch (error) {
            console.error('Error during analysis:', error);
            showMessage(`Error: ${error.message}`);
        } finally {
            // Hide loading indicator
            loadingDiv.classList.add('hidden');
        }
    }

    // Function to display analysis results
    function displayResults(feedback) {
        // Clear previous results
        resultsDiv.innerHTML = '';
        
        if (feedback.length === 0) {
            showMessage('No issues found. Your code looks good!');
            return;
        }
        
        // Log explanations to console
        console.log('Displaying feedback items with explanations:');
        feedback.forEach((item, index) => {
            console.log(`Feedback item ${index + 1}:`);
            console.log(`- Category: ${item.category}`);
            console.log(`- Message: ${item.message}`);
            console.log(`- Has explanation: ${Boolean(item.explanation)}`);
            if (item.explanation) {
                console.log(`- Explanation: ${item.explanation}`);
            }
            if (item.fix) {
                console.log(`- Has fix: true`);
            }
        });
        
        // Create a document fragment to improve performance
        const fragment = document.createDocumentFragment();
        
        // Count issues by category
        const categoryCounts = {
            syntax_error: 0,
            runtime_error: 0,
            fatal_error: 0,
            bad_habit: 0,
            potential_error: 0
        };
        
        feedback.forEach(item => {
            if (item.category) {
                categoryCounts[item.category] = (categoryCounts[item.category] || 0) + 1;
            }
        });
        
        // Add a header explaining the results with category breakdown
        const headerDiv = document.createElement('div');
        headerDiv.className = 'results-header';
        
        let headerHTML = `<p>Found <strong>${feedback.length}</strong> issues in your code:</p>`;
        headerHTML += '<ul class="category-summary">';
        
        if (categoryCounts.syntax_error > 0) {
            headerHTML += `<li><span class="syntax-error-dot"></span> ${categoryCounts.syntax_error} Syntax Error${categoryCounts.syntax_error !== 1 ? 's' : ''}</li>`;
        }
        if (categoryCounts.fatal_error > 0) {
            headerHTML += `<li><span class="fatal-error-dot"></span> ${categoryCounts.fatal_error} Fatal Error${categoryCounts.fatal_error !== 1 ? 's' : ''}</li>`;
        }
        if (categoryCounts.runtime_error > 0) {
            headerHTML += `<li><span class="runtime-error-dot"></span> ${categoryCounts.runtime_error} Runtime Error${categoryCounts.runtime_error !== 1 ? 's' : ''}</li>`;
        }
        if (categoryCounts.potential_error > 0) {
            headerHTML += `<li><span class="potential-error-dot"></span> ${categoryCounts.potential_error} Potential Error${categoryCounts.potential_error !== 1 ? 's' : ''}</li>`;
        }
        if (categoryCounts.bad_habit > 0) {
            headerHTML += `<li><span class="bad-habit-dot"></span> ${categoryCounts.bad_habit} Bad Habit${categoryCounts.bad_habit !== 1 ? 's' : ''}</li>`;
        }
        
        headerHTML += '</ul>';
        headerDiv.innerHTML = headerHTML;
        fragment.appendChild(headerDiv);
        
        // Group feedback by line number
        const feedbackByLine = {};
        feedback.forEach(item => {
            const line = item.line;
            if (!feedbackByLine[line]) {
                feedbackByLine[line] = [];
            }
            feedbackByLine[line].push(item);
        });
        
        // Create feedback elements
        for (const line in feedbackByLine) {
            const lineItems = feedbackByLine[line];
            
            lineItems.forEach(item => {
                const feedbackItem = document.createElement('div');
                
                // Set appropriate class for the item based on category
                if (item.source === 'system') {
                    feedbackItem.className = 'feedback-item system-message';
                } else if (item.category) {
                    // Use the category to determine the class
                    feedbackItem.className = `feedback-item ${item.category}`;
                } else if (item.certainty === 'might_error') {
                    // Backward compatibility
                    feedbackItem.className = 'feedback-item potential_error';
                } else {
                    feedbackItem.className = 'feedback-item runtime_error';
                }
                
                // Create feedback icon based on category
                const iconSpan = document.createElement('span');
                iconSpan.className = 'feedback-icon';
                
                // Choose icon based on category
                if (item.category === 'syntax_error') {
                    iconSpan.textContent = '🔍'; // Magnifying glass for syntax errors
                } else if (item.category === 'runtime_error') {
                    iconSpan.textContent = '⚠️'; // Warning for runtime errors
                } else if (item.category === 'fatal_error') {
                    iconSpan.textContent = '❌'; // X for fatal errors
                } else if (item.category === 'bad_habit') {
                    iconSpan.textContent = '💡'; // Light bulb for bad habits
                } else if (item.category === 'potential_error') {
                    iconSpan.textContent = '❓'; // Question mark for potential errors
                } else {
                    iconSpan.textContent = '⚠️'; // Default warning icon
                }
                
                // Create feedback content
                const contentDiv = document.createElement('div');
                contentDiv.className = 'feedback-content';
                
                // Add line number if available
                if (item.line > 0) {
                    const lineDiv = document.createElement('div');
                    lineDiv.className = 'feedback-line';
                    lineDiv.textContent = `Line ${item.line}`;
                    contentDiv.appendChild(lineDiv);
                }
                
                // Add message with category indicator
                const messageDiv = document.createElement('div');
                messageDiv.className = 'feedback-message';
                
                // Create category label
                const categorySpan = document.createElement('span');
                categorySpan.className = 'category-indicator';
                
                // Set category label text based on category
                if (item.category === 'syntax_error') {
                    categorySpan.textContent = 'SYNTAX ERROR: ';
                    categorySpan.className += ' syntax-error-label';
                } else if (item.category === 'runtime_error') {
                    categorySpan.textContent = 'RUNTIME ERROR: ';
                    categorySpan.className += ' runtime-error-label';
                } else if (item.category === 'fatal_error') {
                    categorySpan.textContent = 'FATAL ERROR: ';
                    categorySpan.className += ' fatal-error-label';
                } else if (item.category === 'bad_habit') {
                    categorySpan.textContent = 'BAD HABIT: ';
                    categorySpan.className += ' bad-habit-label';
                } else if (item.category === 'potential_error') {
                    categorySpan.textContent = 'COULD BECOME ERROR: ';
                    categorySpan.className += ' potential-error-label';
                } else if (item.certainty === 'might_error') {
                    // Backward compatibility
                    categorySpan.textContent = 'MIGHT ERROR: ';
                    categorySpan.className += ' potential-error-label';
                } else {
                    categorySpan.textContent = 'ERROR: ';
                    categorySpan.className += ' runtime-error-label';
                }
                
                messageDiv.appendChild(categorySpan);
                messageDiv.appendChild(document.createTextNode(item.message));
                
                contentDiv.appendChild(messageDiv);
                
                // Add AI explanation if available
                if (item.explanation) {
                    console.log(`Rendering explanation for item at line ${item.line}: ${item.explanation.substring(0, 50)}...`);
                    const aiHelpDiv = document.createElement('div');
                    aiHelpDiv.className = 'ai-help';
                    
                    // Create explanation section
                    const explanationDiv = document.createElement('div');
                    explanationDiv.className = 'explanation';
                    
                    // Create explanation header
                    const explanationHeader = document.createElement('div');
                    explanationHeader.className = 'explanation-header';
                    explanationHeader.textContent = 'Explanation:';
                    explanationDiv.appendChild(explanationHeader);
                    
                    // Create explanation content
                    const explanationContent = document.createElement('div');
                    explanationContent.className = 'explanation-content';
                    explanationContent.textContent = item.explanation;
                    explanationDiv.appendChild(explanationContent);
                    
                    aiHelpDiv.appendChild(explanationDiv);
                    
                    // Add fix if available
                    if (item.fix) {
                        console.log(`Rendering fix for item at line ${item.line}`);
                        const fixDiv = document.createElement('div');
                        fixDiv.className = 'fix';
                        
                        // Create fix header
                        const fixHeader = document.createElement('div');
                        fixHeader.className = 'fix-header';
                        fixHeader.textContent = 'Fix:';
                        fixDiv.appendChild(fixHeader);
                        
                        // Create fix content with code highlighting
                        const fixContent = document.createElement('div');
                        fixContent.className = 'fix-content';
                        
                        // Check if the fix contains code blocks
                        if (item.fix.includes('```python')) {
                            // Parse the fix content to extract and format code blocks
                            const fixText = item.fix;
                            const parts = fixText.split('```python');
                            
                            // Handle the text before the first code block
                            const beforeBlock = document.createElement('div');
                            beforeBlock.textContent = parts[0];
                            fixContent.appendChild(beforeBlock);
                            
                            // Process each code block
                            for (let i = 1; i < parts.length; i++) {
                                const codeAndRest = parts[i].split('```');
                                const code = codeAndRest[0];
                                
                                // Create a formatted code block
                                const codeBlock = document.createElement('pre');
                                const codeElement = document.createElement('code');
                                codeElement.className = 'language-python';
                                codeElement.textContent = code;
                                codeBlock.appendChild(codeElement);
                                fixContent.appendChild(codeBlock);
                                
                                // Apply syntax highlighting
                                hljs.highlightElement(codeElement);
                                
                                // Add any text after the code block
                                if (codeAndRest.length > 1 && codeAndRest[1].trim()) {
                                    const afterCode = document.createElement('div');
                                    afterCode.textContent = codeAndRest[1];
                                    fixContent.appendChild(afterCode);
                                }
                            }
                        } else {
                            // Just display as plain text if no code blocks
                            fixContent.textContent = item.fix;
                        }
                        
                        fixDiv.appendChild(fixContent);
                        
                        aiHelpDiv.appendChild(fixDiv);
                    }
                    
                    contentDiv.appendChild(aiHelpDiv);
                }
                
                // Add source
                const sourceDiv = document.createElement('div');
                sourceDiv.className = 'feedback-source';
                sourceDiv.textContent = `Detected by: ${item.source}`;
                contentDiv.appendChild(sourceDiv);
                
                // Assemble feedback item
                feedbackItem.appendChild(iconSpan);
                feedbackItem.appendChild(contentDiv);
                
                fragment.appendChild(feedbackItem);
            });
        }
        
        // Add all feedback items to the results div
        resultsDiv.appendChild(fragment);
    }

    // Function to show a message in the results div
    function showMessage(message) {
        resultsDiv.innerHTML = `<p class="initial-message">${message}</p>`;
    }
    
    // Initialize highlight.js
    hljs.configure({
        languages: ['python']
    });
});