/**
 * Python Help - Easter Egg Hunt - Shared Library
 * 
 * This file implements the Easter egg hunt functionality for the Python Help website.
 * Using local storage for egg tracking until Supabase integration is fixed.
 */

// Local storage keys
const STORAGE_KEYS = {
  USER_ID: 'easterEggUserId',
  FOUND_EGGS: 'easterEggFound',
  EGG_COUNT: 'easterEggCount'
}

// Egg definitions
const EGGS = {
  PY001: { code: 'PY001', website: 'Python Help', location: 'In the analyzer results' }
}

/**
 * Get or create a user ID for tracking egg collection
 */
const getUserId = () => {
  // Check if we already have an ID in localStorage
  let userId = localStorage.getItem(STORAGE_KEYS.USER_ID)
  
  if (!userId) {
    // Generate a new ID
    userId = 'user_' + Math.random().toString(36).substring(2, 15)
    localStorage.setItem(STORAGE_KEYS.USER_ID, userId)
    
    // Initialize empty found eggs array
    localStorage.setItem(STORAGE_KEYS.FOUND_EGGS, JSON.stringify([]))
    localStorage.setItem(STORAGE_KEYS.EGG_COUNT, '0')
  }
  
  return userId
}

/**
 * Record that a user found an egg
 */
const findEgg = (eggCode) => {
  // Get user ID
  const userId = getUserId()
  
  // Check if the egg code is valid
  if (!EGGS[eggCode]) {
    return { success: false, message: 'Invalid egg code' }
  }
  
  // Get found eggs from local storage
  const foundEggsStr = localStorage.getItem(STORAGE_KEYS.FOUND_EGGS) || '[]'
  const foundEggs = JSON.parse(foundEggsStr)
  
  // Check if this egg has already been found
  if (foundEggs.includes(eggCode)) {
    return { success: false, message: 'You already found this egg!' }
  }
  
  // Add the egg to the found eggs list
  foundEggs.push(eggCode)
  localStorage.setItem(STORAGE_KEYS.FOUND_EGGS, JSON.stringify(foundEggs))
  
  // Update the egg count
  const count = foundEggs.length
  localStorage.setItem(STORAGE_KEYS.EGG_COUNT, count.toString())
  
  return { 
    success: true, 
    message: 'Egg found!', 
    count: count,
    completedHunt: count >= 15
  }
}

/**
 * Get the user's current egg collection progress
 */
const getEggProgress = () => {
  // Get user ID
  getUserId() // Ensure user ID exists
  
  // Get found eggs from local storage
  const foundEggsStr = localStorage.getItem(STORAGE_KEYS.FOUND_EGGS) || '[]'
  const foundEggs = JSON.parse(foundEggsStr)
  
  // Count the eggs
  const count = foundEggs.length
  
  return { 
    count: count, 
    total: 15, 
    completed: count >= 15 
  }
}

/**
 * Create and add the egg counter UI to the page
 */
const addEggCounterUI = async () => {
  const progress = await getEggProgress()
  
  // Create the counter element
  const eggCounter = document.createElement('div')
  eggCounter.className = 'egg-counter'
  eggCounter.innerHTML = `
    <img src="/static/easter-egg-high-quality-4k-ultra-hd-hdr-free-photo-removebg-preview.png" class="egg-icon" style="width: 24px; height: auto;">
    <span class="egg-count">${progress.count}/15</span>
  `
  document.body.appendChild(eggCounter)
  
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
 * Add the Easter egg to the analyzer results
 */
const addEggToResults = () => {
  // Wait for results to be displayed
  const resultsObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
        const resultsDiv = document.getElementById('results')
        if (resultsDiv && resultsDiv.children.length > 0 && !document.querySelector('.hidden-egg')) {
          // Add the egg to the results
          const egg = document.createElement('div')
          egg.className = 'hidden-egg'
          egg.innerHTML = '🥚'
          egg.style.position = 'absolute'
          egg.style.bottom = '10px'
          egg.style.right = '10px'
          egg.style.opacity = '0.15'
          egg.style.fontSize = '24px'
          
          egg.addEventListener('click', async () => {
            const result = await findEgg('PY001')
            showNotification(result.message)
          })
          
          // Make sure the results container has position relative
          if (window.getComputedStyle(resultsDiv).position === 'static') {
            resultsDiv.style.position = 'relative'
          }
          
          resultsDiv.appendChild(egg)
        }
      }
    })
  })
  
  // Start observing the results div
  const resultsDiv = document.getElementById('results')
  if (resultsDiv) {
    resultsObserver.observe(resultsDiv, { childList: true })
  }
}

// Initialize the Easter egg functionality
document.addEventListener('DOMContentLoaded', () => {
  // Add the egg counter UI
  addEggCounterUI()
  
  // Add the egg to the analyzer results
  addEggToResults()
})

export { findEgg, getEggProgress, addEggCounterUI, showNotification }
