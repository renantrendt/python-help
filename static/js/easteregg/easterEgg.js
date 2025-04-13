/**
 * Easter Egg Hunt - Shared Library
 * 
 * This library provides functionality for the Easter egg hunt across
 * bernardoserrano.com websites. It handles user identification,
 * egg discovery, and communication with Supabase.
 */

import { createClient } from '@supabase/supabase-js'

// Initialize Supabase client - Replace these with your actual Supabase credentials
const supabaseUrl = 'https://qsgzakwiivlrsmhobbma.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFzZ3pha3dpaXZscnNtaG9iYm1hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ1MTIzMDgsImV4cCI6MjA2MDA4ODMwOH0.qjDPDeMdCA_IznASy1Hrv0O2kC9hgeRW9ed5IKZ9-44Y'
const supabase = createClient(supabaseUrl, supabaseKey)

/**
 * Get or create a user ID for tracking egg collection
 * @returns {Promise<string|null>} The user's UUID in Supabase
 */
const getUserId = async () => {
  // Check if we already have an ID in localStorage
  let anonymousId = localStorage.getItem('easterEggUserId')
  
  if (!anonymousId) {
    // Generate a new anonymous ID
    anonymousId = 'anon_' + Math.random().toString(36).substring(2, 15)
    localStorage.setItem('easterEggUserId', anonymousId)
    
    // Register this user in Supabase
    await supabase
      .from('users')
      .insert({ anonymous_id: anonymousId })
  }
  
  // Get the UUID from Supabase
  const { data, error } = await supabase
    .from('users')
    .select('id')
    .eq('anonymous_id', anonymousId)
    .single()
    
  if (error) {
    console.error('Error fetching user:', error)
    return null
  }
  
  return data.id
}

/**
 * Record that a user found an egg
 * @param {string} eggCode - The unique code for the egg
 * @returns {Promise<Object>} Result of the operation
 */
const findEgg = async (eggCode) => {
  const userId = await getUserId()
  if (!userId) return { success: false, message: 'Could not identify user' }
  
  // First, get the egg ID from the code
  const { data: eggData, error: eggError } = await supabase
    .from('eggs')
    .select('id')
    .eq('egg_code', eggCode)
    .single()
    
  if (eggError || !eggData) {
    return { success: false, message: 'Invalid egg code' }
  }
  
  // Record that this user found this egg
  const { error: recordError } = await supabase
    .from('user_eggs')
    .insert({ 
      user_id: userId, 
      egg_id: eggData.id 
    })
    
  if (recordError) {
    // If it's a unique violation, the user already found this egg
    if (recordError.code === '23505') {
      return { success: false, message: 'You already found this egg!' }
    }
    return { success: false, message: 'Error recording egg find' }
  }
  
  // Get the updated count
  const { data: countData, error: countError } = await supabase
    .from('user_egg_counts')
    .select('eggs_found, completed_hunt')
    .eq('user_id', userId)
    .single()
    
  if (countError) {
    return { success: true, message: 'Egg found!', count: '?' }
  }
  
  return { 
    success: true, 
    message: 'Egg found!', 
    count: countData.eggs_found,
    completedHunt: countData.completed_hunt
  }
}

/**
 * Get the user's current egg collection progress
 * @returns {Promise<Object>} The user's progress
 */
const getEggProgress = async () => {
  const userId = await getUserId()
  if (!userId) return { count: 0, total: 15, completed: false }
  
  const { data, error } = await supabase
    .from('user_egg_counts')
    .select('eggs_found, completed_hunt')
    .eq('user_id', userId)
    .single()
    
  if (error) {
    return { count: 0, total: 15, completed: false }
  }
  
  return { 
    count: data.eggs_found, 
    total: 15, 
    completed: data.completed_hunt 
  }
}

/**
 * Check if user has collected 14 eggs (for the final egg)
 * @returns {Promise<boolean>} Whether the user has 14 or more eggs
 */
const hasCollected14Eggs = async () => {
  const progress = await getEggProgress()
  return progress.count >= 14
}

/**
 * Random chance function (for eggs with probability)
 * @param {number} percentage - Percentage chance (0-100)
 * @returns {boolean} Whether the random chance succeeded
 */
const randomChance = (percentage) => {
  return Math.random() * 100 <= percentage
}

/**
 * Create and add the egg counter UI to the page
 * @returns {Promise<void>}
 */
const addEggCounterUI = async () => {
  const progress = await getEggProgress()
  
  // Create the counter element
  const eggCounter = document.createElement('div')
  eggCounter.className = 'egg-counter'
  eggCounter.innerHTML = `
    <span class="egg-icon">🥚</span>
    <span class="egg-count">${progress.count}/15</span>
  `
  document.body.appendChild(eggCounter)
  
  // Add styles for the counter
  const style = document.createElement('style')
  style.textContent = `
    .egg-counter {
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: rgba(255, 255, 255, 0.8);
      padding: 10px;
      border-radius: 20px;
      display: flex;
      align-items: center;
      gap: 5px;
      z-index: 1000;
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
      cursor: pointer;
      transition: transform 0.3s;
    }
    
    .egg-counter:hover {
      transform: scale(1.1);
    }
    
    .egg-icon {
      font-size: 24px;
    }
    
    .hidden-egg {
      cursor: pointer;
      opacity: 0.2;
      transition: opacity 0.3s, transform 0.3s;
    }
    
    .hidden-egg:hover {
      opacity: 1 !important;
      transform: scale(1.2);
    }
    
    .egg-notification {
      position: fixed;
      top: 20px;
      right: 20px;
      background: #4CAF50;
      color: white;
      padding: 10px 20px;
      border-radius: 5px;
      animation: fadeIn 0.3s, fadeOut 0.3s 2.7s;
      z-index: 1001;
    }
    
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-20px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes fadeOut {
      from { opacity: 1; transform: translateY(0); }
      to { opacity: 0; transform: translateY(-20px); }
    }
  `
  document.head.appendChild(style)
  
  // Update the counter every 30 seconds (in case eggs are found on other sites)
  setInterval(async () => {
    const updatedProgress = await getEggProgress()
    const countElement = document.querySelector('.egg-count')
    if (countElement) {
      countElement.textContent = `${updatedProgress.count}/15`
    }
  }, 30000)
}

/**
 * Show a notification when an egg is found
 * @param {string} message - The message to display
 */
const showNotification = (message) => {
  const notification = document.createElement('div')
  notification.className = 'egg-notification'
  notification.textContent = message
  document.body.appendChild(notification)
  
  // Remove the notification after 3 seconds
  setTimeout(() => {
    notification.remove()
  }, 3000)
}

/**
 * Show the prize for completing the hunt
 * @param {string} prizeDescription - Description of the prize
 */
const showCompletionPrize = (prizeDescription = "A special congratulations from Bernardo!") => {
  // Create styles for the prize modal
  const style = document.createElement('style')
  style.textContent = `
    .prize-modal {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.8);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 3000;
    }
    
    .prize-content {
      background: white;
      padding: 30px;
      border-radius: 10px;
      text-align: center;
      max-width: 500px;
      box-shadow: 0 0 30px gold;
    }
    
    @keyframes pulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.2); }
      100% { transform: scale(1); }
    }
  `
  document.head.appendChild(style)

  const prizeModal = document.createElement('div')
  prizeModal.className = 'prize-modal'
  prizeModal.innerHTML = `
    <div class="prize-content">
      <h2>Congratulations!</h2>
      <p>You've found all 15 Easter eggs across my websites!</p>
      <p>Your prize is: ${prizeDescription}</p>
      <button id="close-prize">Close</button>
    </div>
  `
  document.body.appendChild(prizeModal)
  
  document.getElementById('close-prize').addEventListener('click', () => {
    prizeModal.remove()
  })
}

// Export all functions
export { 
  findEgg, 
  getEggProgress, 
  hasCollected14Eggs, 
  randomChance, 
  addEggCounterUI,
  showNotification,
  showCompletionPrize
}
