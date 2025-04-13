/**
 * Python Help - Easter Egg Implementation
 * 
 * This file implements the Easter egg hunt functionality for the Python Help website.
 */

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm'

// Initialize Supabase client
const supabaseUrl = 'https://qsgzakwiivlrsmhobbma.supabase.co'
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFzZ3pha3dpaXZscnNtaG9iYm1hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ1MTIzMDgsImV4cCI6MjA2MDA4ODMwOH0.qjDPDeMdCA_IznASy1Hrv0O2kC9hgeRW9ed5IKZ9-44Y'
const supabase = createClient(supabaseUrl, supabaseKey)

/**
 * Get or create a user ID for tracking egg collection
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
