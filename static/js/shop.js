       document.addEventListener('DOMContentLoaded', function() {
            // Filter functionality
            const searchFilter = document.getElementById('searchFilter');
            const categoryFilter = document.getElementById('categoryFilter');
            const sortFilter = document.getElementById('sortFilter');
            const priceFilter = document.getElementById('priceFilter');
            const productCards = document.querySelectorAll('.product-card');

            function filterProducts() {
                const searchText = searchFilter.value.toLowerCase();
                const category = categoryFilter.value;
                const sortBy = sortFilter.value;
                const priceRange = priceFilter.value;

                let filteredProducts = Array.from(productCards).filter(card => {
                    const productName = card.querySelector('.product-title').textContent.toLowerCase();
                    const productCategory = card.dataset.category;
                    const productPrice = parseFloat(card.dataset.price);

                    // Check search
                    const matchesSearch = productName.includes(searchText);

                    // Check category
                    const matchesCategory = !category || productCategory === category;

                    // Check price range
                    let matchesPrice = true;
                    if (priceRange) {
                        if (priceRange === '0-25') matchesPrice = productPrice <= 25;
                        else if (priceRange === '25-50') matchesPrice = productPrice > 25 && productPrice <= 50;
                        else if (priceRange === '50-100') matchesPrice = productPrice > 50 && productPrice <= 100;
                        else if (priceRange === '100+') matchesPrice = productPrice > 100;
                    }

                    return matchesSearch && matchesCategory && matchesPrice;
                });

                // Sort products
                filteredProducts.sort((a, b) => {
                    const ratingA = parseFloat(a.dataset.rating);
                    const ratingB = parseFloat(b.dataset.rating);
                    const priceA = parseFloat(a.dataset.price);
                    const priceB = parseFloat(b.dataset.price);
                    const newA = parseInt(a.dataset.new);
                    const newB = parseInt(b.dataset.new);

                    switch(sortBy) {
                        case 'rating':
                            return ratingB - ratingA;
                        case 'price_low':
                            return priceA - priceB;
                        case 'price_high':
                            return priceB - priceA;
                        case 'new':
                            return newB - newA;
                        default:
                            return 0;
                    }
                });

                // Hide all products
                productCards.forEach(card => card.style.display = 'none');

                // Show filtered products
                filteredProducts.forEach(card => card.style.display = 'block');
            }

            // Add event listeners
            searchFilter.addEventListener('input', filterProducts);
            categoryFilter.addEventListener('change', filterProducts);
            sortFilter.addEventListener('change', filterProducts);
            priceFilter.addEventListener('change', filterProducts);

            // Add to cart functionality
            document.querySelectorAll('.add-to-cart').forEach(button => {
                button.addEventListener('click', function() {
                    const productId = this.dataset.productId;
                    const productName = this.dataset.productName;

                    fetch(`/add_to_cart/${productId}`, {
                        method: 'GET'
                    })
                    .then(response => {
                        if (response.ok) {
                            alert(`"${productName}" added to cart!`);
                        } else {
                            alert('Error adding to cart');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Error adding to cart');
                    });
                });
            });

            // Header search
            const headerSearch = document.getElementById('searchInput');
            headerSearch.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchFilter.value = this.value;
                    filterProducts();
                    window.scrollTo({ top: document.querySelector('.filters-section').offsetTop - 100, behavior: 'smooth' });
                }
            });
        });