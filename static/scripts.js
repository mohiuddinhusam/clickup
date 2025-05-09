window.addEventListener("scroll", () => {
  const nav = document.querySelector("nav");
  if (window.scrollY > 50) {
    nav.classList.add("scrolled");
  } else {
    nav.classList.remove("scrolled");
  }
});


let currentAuthMode = 'login';

function openAuthModal(mode) {
  currentAuthMode = mode;
  document.getElementById('authTitle').textContent = mode === 'login' ? 'Login' : 'Sign Up';
  document.querySelector('.auth-btn').textContent = mode === 'login' ? 'Login' : 'Sign Up';
  document.querySelector('.switch-auth').innerHTML = mode === 'login' ? 
    'Not registered? <a href="#" onclick="toggleAuthMode()">Sign up</a>' : 
    'Already have an account? <a href="#" onclick="toggleAuthMode()">Login</a>';
  
  document.getElementById('roleGroup').style.display = mode === 'signup' ? 'block' : 'none';
  document.getElementById('authModal').style.display = 'flex';
}

function toggleAuthMode() {
  currentAuthMode = currentAuthMode === 'login' ? 'signup' : 'login';
  document.getElementById('authTitle').textContent = currentAuthMode === 'login' ? 'Login' : 'Sign Up';
  document.querySelector('.auth-btn').textContent = currentAuthMode === 'login' ? 'Login' : 'Sign Up';
  document.querySelector('.switch-auth').innerHTML = currentAuthMode === 'login' ? 
    'Not registered? <a href="#" onclick="toggleAuthMode()">Sign up</a>' : 
    'Already have an account? <a href="#" onclick="toggleAuthMode()">Login</a>';
  
  document.getElementById('roleGroup').style.display = currentAuthMode === 'signup' ? 'block' : 'none';
}

function closeAuthModal() {
  document.getElementById('authModal').style.display = 'none';
}

function closeCommentsModal() {
  document.getElementById("commentsModal").style.display = "none";
}


async function handleLogout() {
  try {
    const response = await fetch('/logout');
    const data = await response.json();
    
    if (data.success) {
      showNotification('Logged out successfully', 'success');
      setTimeout(() => {
        window.location.href = '/';
      }, 1000);
    } else {
      throw new Error(data.error || 'Failed to logout');
    }
  } catch (error) {
    showNotification(error.message || 'Failed to logout', 'error');
  }
}


function showNotification(message, type = 'info') {
  
  const existingNotifications = document.querySelectorAll('.notification');
  existingNotifications.forEach(notification => {
    document.body.removeChild(notification);
  });
  
  
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  
  const icon = document.createElement('i');
  icon.className = type === 'success' ? 'fas fa-check-circle' : 
                   type === 'error' ? 'fas fa-exclamation-circle' : 
                   'fas fa-info-circle';
  
  notification.appendChild(icon);
  notification.appendChild(document.createTextNode(message));
  
  
  document.body.appendChild(notification);
  
  
  setTimeout(() => {
    notification.style.opacity = '0';
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification);
      }
    }, 300);
  }, 3000);
}

document.addEventListener("DOMContentLoaded", function () {
  
  const mobileToggle = document.querySelector(".mobile-menu-toggle");
  if (mobileToggle) {
    mobileToggle.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      document.querySelector(".sidebar").classList.toggle("mobile-active");
    });
    
    
    document.addEventListener('click', function(e) {
      const sidebar = document.querySelector(".sidebar");
      const isMenuOpen = sidebar.classList.contains("mobile-active");
      const isClickInside = sidebar.contains(e.target) || mobileToggle.contains(e.target);
      
      if (isMenuOpen && !isClickInside) {
        sidebar.classList.remove("mobile-active");
      }
    });
  }

  
  document.querySelectorAll(".like-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      const videoId = this.closest(".reel-card").dataset.videoId;
      handleLike(this, videoId);
    });
  });

  
  document.querySelectorAll(".comment-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      const videoId = this.closest(".reel-card").dataset.videoId;
      openCommentsModal(videoId);
    });
  });

  
  const commentsModal = document.getElementById("commentsModal");
  if (commentsModal) {
    const commentInput = document.getElementById("commentInput");
    const postBtn = document.getElementById("postComment");
    let activeVideoId = null;

    postBtn.addEventListener("click", () => {
      const comment = commentInput.value.trim();
      if (comment && activeVideoId) {
        postComment(activeVideoId, comment);
      }
    });

    commentInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        const comment = commentInput.value.trim();
        if (comment && activeVideoId) {
          postComment(activeVideoId, comment);
        }
      }
    });

    window.openCommentsModal = function(videoId) {
      activeVideoId = videoId;
      loadComments(videoId);
      commentsModal.style.display = "flex";
    };

    window.closeCommentsModal = function() {
      commentsModal.style.display = "none";
      activeVideoId = null;
    };
  }

  
  setupVideos();
  
  
  setupSearch();
  
  
  const authForm = document.getElementById('authForm');
  if (authForm) {
    authForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const username = document.getElementById('username').value;
      const password = document.getElementById('password').value;
      
      if (!username || !password) {
        showNotification('Please fill in all required fields', 'error');
        return;
      }
      
      try {
        let endpoint, data;
        
        if (currentAuthMode === 'login') {
          endpoint = '/login';
          data = { username, password };
        } else {
          const role = document.getElementById('role').value;
          endpoint = '/signup';
          data = { username, password, role };
        }
        
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
          showNotification(
            currentAuthMode === 'login' ? 'Login successful!' : 'Account created successfully!', 
            'success'
          );
          
          closeAuthModal();
          
          if (currentAuthMode === 'login') {
            setTimeout(() => {
              window.location.reload();
            }, 1000);
          } else {
            
            setTimeout(() => {
              openAuthModal('login');
            }, 1000);
          }
        } else {
          throw new Error(result.error);
        }
      } catch (error) {
        showNotification(error.message, 'error');
      }
    });
  }
});

async function handleLike(btn, videoId) {
  try {
    
    const response = await fetch(`/like/${videoId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });
    
    if (response.status === 401) {
      
      showNotification("Please log in to like videos", "error");
      openAuthModal('login');
      return;
    }
    
    const data = await response.json();
    
    if (data.error) {
      throw new Error(data.error);
    }

    
    btn.classList.toggle("active");
    const countElement = btn.querySelector(".count");
    if (countElement) {
      countElement.textContent = data.likes;
    }
    
    showNotification(btn.classList.contains("active") ? "Added to liked videos" : "Removed from liked videos", "success");
  } catch (error) {
    console.error("Error liking video:", error);
    showNotification("Failed to update like status", "error");
  }
}

async function loadComments(videoId) {
  try {
    const response = await fetch(`/comments/${videoId}`);
    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    const container = document.querySelector(".comments-container");
    
    if (data.comments.length === 0) {
      container.innerHTML = '<div class="empty-comments">No comments yet. Be the first to comment!</div>';
      return;
    }
    
    container.innerHTML = data.comments
      .map(
        (comment) => `
          <div class="comment">
              <div class="comment-user">${comment.username}</div>
              <div class="comment-text">${comment.text}</div>
              <div class="comment-time">${formatTime(comment.timestamp)}</div>
          </div>
        `
      )
      .join("");
      
    
    container.scrollTop = container.scrollHeight;
  } catch (error) {
    console.error("Error loading comments:", error);
    showNotification("Failed to load comments", "error");
  }
}

async function postComment(videoId, text) {
  try {
    const response = await fetch(`/comment/${videoId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ comment: text }),
    });
    
    if (response.status === 401) {
      showNotification("Please log in to comment", "error");
      openAuthModal('login');
      return;
    }

    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    
    document.getElementById("commentInput").value = "";
    await loadComments(videoId);

    
    const commentBtn = document.querySelector(
      `.reel-card[data-video-id="${videoId}"] .comment-btn .count`
    );
    if (commentBtn) {
      const currentCount = parseInt(commentBtn.textContent || "0");
      commentBtn.textContent = currentCount + 1;
    }

    showNotification("Comment posted successfully", "success");
  } catch (error) {
    console.error("Error posting comment:", error);
    showNotification("Failed to post comment", "error");
  }
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);

  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return date.toLocaleDateString();
}

function setupVideos() {
  const videos = document.querySelectorAll('.reel-video');
  
  videos.forEach(video => {
    const card = video.closest('.reel-card');
    if (!card) return;
    
    const playPauseBtn = card.querySelector('.play-pause-btn'); // Find the play/pause button
    const muteBtn = card.querySelector('.mute-btn'); // Find the mute button

    // Play/Pause button logic
    if (playPauseBtn) {
      playPauseBtn.addEventListener('click', () => {
        if (video.paused) {
          video.play();
          playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
        } else {
          video.pause();
          playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
        }
      });
    }
    
    // Mute button logic
    if (muteBtn) {
      muteBtn.addEventListener('click', () => {
        video.muted = !video.muted;
        muteBtn.innerHTML = video.muted ? 
          '<i class="fas fa-volume-mute"></i>' : 
          '<i class="fas fa-volume-up"></i>';
      });
    }
  });
}
function setupAutoPlayOnScroll() {
  const videos = document.querySelectorAll('.reel-video');
  
  window.addEventListener('scroll', () => {
    videos.forEach(video => {
      const rect = video.getBoundingClientRect();
      const isInViewport = rect.top >= 0 && rect.bottom <= window.innerHeight;
      
      if (isInViewport) {
        if (video.paused) video.play();
      } else {
        if (!video.paused) video.pause();
      }
    });
  });
}
document.addEventListener("DOMContentLoaded", function () {
  setupVideos();
  setupAutoPlayOnScroll();
});



function setupSearch() {
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        const query = searchInput.value.trim();
        if (query) {
          window.location.href = `/?search=${encodeURIComponent(query)}`;
        } else {
          window.location.href = '/';
        }
      }
    });
  }
}


window.addEventListener("DOMContentLoaded", function() {
  function handleScreenSizeChanges() {
    const isNarrowScreen = window.innerWidth <= 768;
    document.body.classList.toggle('narrow-screen', isNarrowScreen);
    
    
    const content = document.querySelector('.content');
    if (content) {
      content.style.marginTop = isNarrowScreen ? '110px' : '60px';
    }
  }
  
  
  handleScreenSizeChanges();
  
  
  window.addEventListener('resize', handleScreenSizeChanges);
});
