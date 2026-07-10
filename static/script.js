const form = document.getElementById("ppt-form");
const btn = document.getElementById("generate-btn");
const buttonText = btn.querySelector(".button-text");
const buttonIcon = btn.querySelector(".button-icon");
const status = document.getElementById("status");

const generationStages = [
  "Analyzing your presentation idea...",
  "Structuring the narrative...",
  "AI is critiquing the storyline...",
  "Refining presentation flow...",
  "Writing slide content...",
  "Directing slide visuals...",
  "Building your presentation..."
];

let stageInterval = null;

function startGenerationStages() {
  let currentStage = 0;

  status.textContent = generationStages[currentStage];
  status.className = "status generating";

  stageInterval = setInterval(() => {
    currentStage += 1;

    if (currentStage >= generationStages.length) {
      currentStage = generationStages.length - 1;

      clearInterval(stageInterval);
      stageInterval = null;
    }

    status.textContent = generationStages[currentStage];
  }, 4500);
}

function stopGenerationStages() {
  if (stageInterval !== null) {
    clearInterval(stageInterval);
    stageInterval = null;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const title = document
    .getElementById("title")
    .value
    .trim();

  const num_slides = document
    .getElementById("num_slides")
    .value;

  const tone = document
    .getElementById("tone")
    .value;

  const audience =
    document
      .getElementById("audience")
      .value
      .trim()
    || "general professional audience";

  if (!title) {
    status.textContent =
      "Enter a presentation idea to continue.";

    status.className = "status error";

    return;
  }

  btn.disabled = true;

  buttonText.textContent =
    "Generating Presentation";

  buttonIcon.textContent = "✦";

  btn.classList.add("generating");

  startGenerationStages();

  try {
    const response = await fetch("/generate", {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        title,
        num_slides,
        tone,
        audience
      })
    });

    if (!response.ok) {
      const errData = await response
        .json()
        .catch(() => ({}));

      throw new Error(
        errData.error
        || "Presentation generation failed."
      );
    }

    const blob = await response.blob();

    const url =
      window.URL.createObjectURL(blob);

    const downloadLink =
      document.createElement("a");

    downloadLink.href = url;

    downloadLink.download =
      `${title.replace(
        /[^a-z0-9_\- ]/gi,
        ""
      )}.pptx`;

    document.body.appendChild(
      downloadLink
    );

    downloadLink.click();

    downloadLink.remove();

    window.URL.revokeObjectURL(url);

    stopGenerationStages();

    status.textContent =
      "Presentation ready. Your PowerPoint has been downloaded.";

    status.className =
      "status success";

  } catch (error) {

    stopGenerationStages();

    status.textContent =
      error.message;

    status.className =
      "status error";

  } finally {

    btn.disabled = false;

    btn.classList.remove("generating");

    buttonText.textContent =
      "Generate Presentation";

    buttonIcon.textContent = "✦";
  }
});