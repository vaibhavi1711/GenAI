// Script for Newspaper Article Generator

// Add loading state to generate button when form is submitted
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const generateBtn = document.getElementById('generateBtn');
    
    if (form && generateBtn) {
        form.addEventListener('submit', function() {
            // Add loading state
            generateBtn.classList.add('loading');
            generateBtn.innerHTML = 'Generating...';
            generateBtn.disabled = true;
        });
    }
    
    // File upload validation
    const fileInput = document.getElementById('document');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const fileSizeLimit = 16 * 1024 * 1024; // 16MB
            const file = this.files[0];
            
            if (file && file.size > fileSizeLimit) {
                alert('File size exceeds 16MB limit. Please choose a smaller file.');
                this.value = ''; // Clear the file input
            }
            
            // Check file extension
            if (file) {
                const fileName = file.name;
                const fileExt = fileName.split('.').pop().toLowerCase();
                const allowedExtensions = ['txt', 'pdf', 'doc', 'docx'];
                
                if (!allowedExtensions.includes(fileExt)) {
                    alert('Invalid file type. Allowed types: TXT, PDF, DOC, DOCX');
                    this.value = ''; // Clear the file input
                }
            }
        });
    }
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    if (alerts.length > 0) {
        setTimeout(() => {
            alerts.forEach(alert => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);
    }
});
