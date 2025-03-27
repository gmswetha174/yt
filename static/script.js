document.getElementById("translate-btn").addEventListener("click", function () {
    let url = document.getElementById("url").value;
    let language = document.getElementById("language").value;
    let progressBar = document.getElementById("progress-bar");
    let progressContainer = document.getElementById("progress-container");
    let progressText = document.getElementById("progress-text");
    let successMessage = document.getElementById("success-message");

    if (!url) {
        alert("Please enter a YouTube URL.");
        return;
    }

    // Show progress initially
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
                    setTimeout(updateProgress, 1000);
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
    
        // Hide progress bar after completion
        progressContainer.style.display = "none";
        successMessage.style.display = "block";
    
        // Set translated text
        document.getElementById("translated-text").innerText = data.translated_text;
        document.getElementById("summarized-text").innerText = data.summarized_text;
    
        // Check if audio file exists before playing
        if (data.audio_file) {
            document.getElementById("audio-source").src = data.audio_file;
            document.getElementById("translated-audio").load();
            document.getElementById("translated-audio").play();
        }
    })
    .catch(error => {
        console.error("Error:", error);
        alert("An error occurred.");
    });
    
});
