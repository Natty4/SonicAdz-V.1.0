/**
 * Form Validation component
 * Handles form validation for login, signup, and other forms
 */

document.addEventListener("DOMContentLoaded", () => {

  // Password toggle functionality
  const passwordToggles = document.querySelectorAll(".password-toggle")

  passwordToggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const passwordInput = toggle.previousElementSibling
      const icon = toggle.querySelector("i")

      if (passwordInput.type === "password") {
        passwordInput.type = "text"
        icon.classList.remove("fa-eye")
        icon.classList.add("fa-eye-slash")
      } else {
        passwordInput.type = "password"
        icon.classList.remove("fa-eye-slash")
        icon.classList.add("fa-eye")
      }
    })
  })

  // Real-time validation
  const formInputs = document.querySelectorAll("input[required]")
  formInputs.forEach((input) => {
    input.addEventListener("blur", () => {
      validateInput(input)
    })

    input.addEventListener("input", () => {
      const errorElement = document.getElementById(`${input.id}-error`)
      if (errorElement && errorElement.textContent) {
        validateInput(input)
      }
    })
  })

  function validateInput(input) {
    const errorElement = document.getElementById(`${input.id}-error`)
    if (!errorElement) return

    switch (input.id) {
      case "name":
        if (!input.value.trim()) {
          errorElement.textContent = "Name is required"
          input.classList.add("error")
        } else {
          errorElement.textContent = ""
          input.classList.remove("error")
        }
        break

      case "email":
        if (!input.value.trim()) {
          errorElement.textContent = "Email is required"
          input.classList.add("error")
        } else if (!isValidEmail(input.value.trim())) {
          errorElement.textContent = "Please enter a valid email address"
          input.classList.add("error")
        } else {
          errorElement.textContent = ""
          input.classList.remove("error")
        }
        break

      case "password":
        if (!input.value) {
          errorElement.textContent = "Password is required"
          input.classList.add("error")
        } else if (input.value.length < 8) {
          errorElement.textContent = "Password must be at least 8 characters"
          input.classList.add("error")
        } else {
          errorElement.textContent = ""
          input.classList.remove("error")
        }
        break

      case "confirm-password":
        const passwordInput = document.getElementById("password")
        if (!input.value) {
          errorElement.textContent = "Please confirm your password"
          input.classList.add("error")
        } else if (input.value !== passwordInput.value) {
          errorElement.textContent = "Passwords do not match"
          input.classList.add("error")
        } else {
          errorElement.textContent = ""
          input.classList.remove("error")
        }
        break
    }
  }
})
