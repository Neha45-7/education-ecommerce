document.addEventListener("DOMContentLoaded", function () {
  // Automatically hide flash messages
  setTimeout(function () {
    const messages = document.querySelectorAll(".flash");

    messages.forEach(function (message) {
      message.style.display = "none";
    });
  }, 3000);

  // Confirmation before removing items
  const deleteButtons = document.querySelectorAll(".danger-btn");

  deleteButtons.forEach(function (button) {
    button.addEventListener("click", function (event) {
      if (!confirm("Remove this item from cart?")) {
        event.preventDefault();
      }
    });
  });
});
