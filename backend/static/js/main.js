// In your main JavaScript file
document.addEventListener('DOMContentLoaded', function() {
    // Handle dropdown menu clicks
    document.querySelectorAll('.dropdown-item[data-modal-target]').forEach(item => {
        item.addEventListener('click', async function(e) {
            e.preventDefault();
            const target = this.getAttribute('data-modal-target');
            const url = this.getAttribute('href');
            
            try {
                const modal = new bootstrap.Modal(document.getElementById('dynamicModal'));
                const modalContent = document.getElementById('modalContent');
                
                // Show loading state
                modalContent.innerHTML = `
                    <div class="text-center py-5">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2">Loading ${target.replace('-', ' ')}...</p>
                    </div>
                `;
                
                modal.show();
                
                // Fetch content
                const response = await fetch(url);
                if (!response.ok) throw new Error('Failed to load');
                const html = await response.text();
                modalContent.innerHTML = html;
                
            } catch (error) {
                console.error('Error:', error);
                modalContent.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Failed to load content. Please try again.
                    </div>
                `;
            }
        });
    });
});