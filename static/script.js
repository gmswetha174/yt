document.getElementById("translateButton").addEventListener("click", function () {
    let url = document.getElementById("youtubeUrl").value;
    let language = document.getElementById("languageSelect").value;
    let progressBar = document.getElementById("progressBar");
    let progressContainer = document.getElementById("progressContainer");
    let progressText = document.getElementById("progressText");

    if (!url) {
        alert("Please enter a YouTube URL.");
        return;
    }

    // Show the progress bar initially
    progressBar.style.width = "0%";
    progressContainer.style.display = "block";
    progressText.innerText = "Processing...";

    function updateProgress() {
        fetch(`/progress?url=${encodeURIComponent(url)}`)
        .then(response => response.json())
        .then(data => {
            let progress = data.progress;
            progressBar.style.width = progress + "%";
            progressText.innerText = `Processing... ${progress}%`;

            if (progress < 100) {
                setTimeout(updateProgress, 1000); // Poll every second
            }
        })
        .catch(error => console.error("Error fetching progress:", error));
    }

    updateProgress();

    fetch("/process", {
        method: "POST",
        body: new URLSearchParams({ url: url, language: language }),
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }

        // Hide the progress bar after completion
        progressContainer.style.display = "none";

        // Show success message
        let successMessage = document.createElement("p");
        successMessage.innerText = "✅ Translation Successful!";
        successMessage.style.color = "#00FF00";  // Green color
        successMessage.style.fontWeight = "bold";
        successMessage.style.fontSize = "18px";
        progressContainer.parentElement.appendChild(successMessage);

        document.getElementById("translatedText").innerText = data.translated_text;
        document.getElementById("translatedAudio").src = data.audio_file;
    })
    .catch(error => {
        console.error("Error:", error);
        alert("An error occurred.");
    });
});
