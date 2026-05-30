const root = document.documentElement;
const savedTheme = localStorage.getItem("theme");
if (savedTheme) root.setAttribute("data-bs-theme", savedTheme);

document.getElementById("themeToggle")?.addEventListener("click", () => {
  const next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
  root.setAttribute("data-bs-theme", next);
  localStorage.setItem("theme", next);
});

document.querySelectorAll(".reveal").forEach((button) => {
  button.addEventListener("click", () => {
    const secret = button.parentElement.querySelector(".secret");
    const showing = secret.textContent !== "*****";
    secret.textContent = showing ? "*****" : secret.dataset.value;
    button.textContent = showing ? "查看" : "隐藏";
  });
});
