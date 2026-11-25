/**
 * G0DM0D3 GitHub Integration Module
 * Connects the autonomous AI system with GitHub repositories
 * For learning, analysis, and integration into the EsprieAether system
 */

import express from 'express';
import * as https from 'https';
import * as fs from 'fs';
import * as path from 'path';

// GitHub API Configuration
const GITHUB_CONFIG = {
    BASE_URL: 'https://api.github.com',
    RATE_LIMIT: 5000, // Requests per hour
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000, // ms
    CACHE_TTL: 3600000 // 1 hour cache
};

// Custom Request Class for GitHub API
class GithubAPI {
    token?: string;
    headers: Record<string, string>;

    constructor(token?: string) {
        this.token = token;
        this.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'EsprieAether-Backend/1.0.0'
        };
    }

    private getAuthHeaders(): Record<string, string> {
        const headers = { ...this.headers };
        if (this.token) {
            headers['Authorization'] = `token ${this.token}`;
        }
        return headers;
    }

    async get(endpoint: string, params?: Record<string, string>): Promise<any> {
        return this.request('GET', endpoint, params);
    }

    async post(endpoint: string, data?: any): Promise<any> {
        return this.request('POST', endpoint, data);
    }

    async request(method: string, endpoint: string, data?: any): Promise<any> {
        const url = `${GITHUB_CONFIG.BASE_URL}${endpoint}`;
        const options: any = {
            method,
            headers: this.getAuthHeaders(),
            timeout: 30000
        };

        if (data && (method === 'POST' || method === 'PUT')) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(data);
        }

        // Retry logic
        for (let attempt = 0; attempt < GITHUB_CONFIG.MAX_RETRIES; attempt++) {
            try {
                const response = await fetch(url, options);
                const data = await response.json();

                if (response.status === 403 && response.headers.get('X-RateLimit-Remaining') === '0') {
                    // Rate limit exceeded, wait and retry
                    const resetTime = response.headers.get('X-RateLimit-Reset');
                    if (resetTime) {
                        const waitTime = (parseInt(resetTime) - Date.now()) + 1000;
                        console.log(`⏳ Rate limited. Waiting ${waitTime}ms...`);
                        await new Promise(r => setTimeout(r, waitTime));
                        continue;
                    }
                }

                return data;
            } catch (error: any) {
                if (attempt === GITHUB_CONFIG.MAX_RETRIES - 1) {
                    throw error;
                }
                await new Promise(r => setTimeout(r, 1000));
            }
        }
    }
}

// Repository Analyzer
class RepositoryAnalyzer {
    analyze(repo: any): any {
        const score = this.calculateScore(repo);
        const categories = this.categorize(repo);
        const learningOpportunities = this.identifyOpportunities(repo);

        return {
            name: repo.full_name,
            owner: repo.owner.login,
            description: repo.description,
            stars: repo.stargazers_count,
            forks: repo.forks_count,
            language: repo.language,
            topics: repo.topics,
            createdAt: repo.created_at,
            updatedAt: repo.pushed_at,
            score,
            categories,
            learningOpportunities,
            status: 'analyzed'
        };
    }

    private calculateScore(repo: any): number {
        let score = 0;
        score += repo.stargazers_count / 100;
        score += repo.forks_count / 50;
        score += (repo.language === 'Python' || repo.language === 'TypeScript' || repo.language === 'JavaScript') ? 10 : 0;
        if (repo.topics.includes('automation')) score += 15;
        if (repo.topics.includes('security') || repo.topics.includes('cybersecurity')) score += 20;
        if (repo.topics.includes('ai') || repo.topics.includes('machine-learning')) score += 15;
        if (repo.topics.includes('reverse-engineering')) score += 15;
        return Math.min(score, 100);
    }

    private categorize(repo: any): string[] {
        const categories: string[] = [];
        const topics = repo.topics || [];

        if (topics.includes('automation') || topics.includes('devops') || topics.includes('ci-cd')) {
            categories.push('automation');
        }
        if (topics.includes('security') || topics.includes('cybersecurity') || topics.includes('pentesting')) {
            categories.push('security');
        }
        if (topics.includes('ai') || topics.includes('machine-learning') || topics.includes('deep-learning')) {
            categories.push('ai-ml');
        }
        if (topics.includes('reverse-engineering') || topics.includes('reverse-engineering') || topics.includes('malware-analysis')) {
            categories.push('reverse-engineering');
        }
        if (topics.includes('learning') || topics.includes('tutorial') || topics.includes('education')) {
            categories.push('education');
        }

        return categories.length > 0 ? categories : ['general'];
    }

    private identifyOpportunities(repo: any): string[] {
        const opportunities: string[] = [];
        const description = (repo.description || '').toLowerCase();

        if (repo.language === 'Python') {
            opportunities.push('python-scripts');
        }
        if (repo.language === 'JavaScript' || repo.language === 'TypeScript') {
            opportunities.push('js-typescript');
        }
        if (repo.language === 'Go' || repo.language === 'Rust') {
            opportunities.push('system-language');
        }
        if (description.includes('automation') || description.includes('automate')) {
            opportunities.push('automation-patterns');
        }
        if (description.includes('security') || description.includes('security') || description.includes('hacking') || description.includes('pentest')) {
            opportunities.push('security-patterns');
        }
        if (description.includes('machine learning') || description.includes('ai') || description.includes('model')) {
            opportunities.push('ai-patterns');
        }

        return opportunities;
    }
}

// Learning Path Manager
class LearningPathManager {
    private static instance: LearningPathManager;
    private paths: Map<string, any[]> = new Map();
    private categories: string[] = [
        'automation',
        'security',
        'ai-ml',
        'reverse-engineering',
        'education'
    ];

    static getInstance(): LearningPathManager {
        if (!LearningPathManager.instance) {
            LearningPathManager.instance = new LearningPathManager();
        }
        return LearningPathManager.instance;
    }

    async recommendRepositories(analyzer: RepositoryAnalyzer, category?: string): Promise<any[]> {
        // Get top repositories based on score and category
        const repositories = await this.fetchTopRepositories(category);
        return repositories
            .map(repo => analyzer.analyze(repo))
            .filter(repo => repo.score > 10)
            .sort((a, b) => b.score - a.score)
            .slice(0, 20);
    }

    private async fetchTopRepositories(category?: string): Promise<any[]> {
        const repos: any[] = [];
        const queries = {
            automation: 'language:python automation cf:10',
            security: 'language:python security cf:10',
            'ai-ml': 'language:python ai machine-learning cf:10',
            'reverse-engineering': 'language:c++ reverse-engineering cf:10',
            education: 'language:python tutorial learning education cf:10'
        };

        const query = queries[category || 'automation'] || queries.automation;
        const api = new GithubAPI();

        try {
            const response = await api.get(`/search/repositories?q=${query}&sort=stars&per_page=10`);
            if (Array.isArray(response.items)) {
                repos.push(...response.items);
            }
        } catch (error) {
            console.error('❌ Error fetching repositories:', error);
        }

        return repos;
    }

    addToLearningPath(repo: any, category: string) {
        if (!this.paths.has(category)) {
            this.paths.set(category, []);
        }
        this.paths.get(category).push(repo);

        // Save to persistent storage
        this.saveLearningPath();
    }

    private saveLearningPath() {
        try {
            const data = {
                paths: Object.fromEntries(this.paths),
                lastUpdated: new Date().toISOString()
            };
            fs.writeFileSync(
                path.join(__dirname, '../../data', 'learning_path.json'),
                JSON.stringify(data, null, 2)
            );
        } catch (e) {
            console.error('Error saving learning path:', e);
        }
    }

    getLearningPath(category?: string): any[] {
        if (category) {
            return this.paths.get(category) || [];
        }
        const allPaths = [];
        this.paths.forEach((repos, cat) => {
            if (this.categories.includes(cat)) {
                allPaths.push(...repos);
            }
        });
        return allPaths;
    }

    getCategories(): string[] {
        return [...this.categories];
    }
}

// GitHub Integration API Router
export class GitHubIntegrationRouter {
    private app: express.Application;
    private githubAPI: GithubAPI;
    private analyzer: RepositoryAnalyzer;
    private learningManager: LearningPathManager;

    constructor(token?: string) {
        this.app = express();
        this.githubAPI = new GithubAPI(token);
        this.analyzer = new RepositoryAnalyzer();
        this.learningManager = LearningPathManager.getInstance();
    }

    initialize(): express.Application {
        this.app.use(express.json());

        // Health check
        this.app.get('/api/github/health', (req, res) => {
            res.json({
                status: 'ok',
                integration: 'github',
                timestamp: new Date().toISOString()
            });
        });

        // Search repositories
        this.app.get('/api/github/search', async (req, res) => {
            const { q, limit = 10, sort = 'stars' } = req.query;
            try {
                const results = await this.githubAPI.get(`/search/repositories?q=${q}&sort=${sort}&per_page=${limit}`);
                res.json(results);
            } catch (error) {
                res.status(500).json({ error: 'Failed to search repositories' });
            }
        });

        // Get repository details
        this.app.get('/api/github/repo/:fullName', async (req, res) => {
            const { fullName } = req.params;
            try {
                const repo = await this.githubAPI.get(`/repos/${fullName}`);
                const analysis = this.analyzer.analyze(repo);
                res.json(analysis);
            } catch (error) {
                res.status(404).json({ error: 'Repository not found' });
            }
        });

        // Get repository contents
        this.app.get('/api/github/repo/:fullName/contents', async (req, res) => {
            const { fullName, path = '' } = req.query;
            try {
                const repo = await this.githubAPI.get(`/repos/${fullName}`);
                const contents = await this.githubAPI.get(`/repos/${fullName}/contents/${path || ''}`);
                res.json(contents);
            } catch (error) {
                res.status(404).json({ error: 'Failed to fetch contents' });
            }
        });

        // Get learning recommendations
        this.app.get('/api/github/learning/recommend', async (req, res) => {
            const { category } = req.query;
            try {
                const recommendations = await this.learningManager.recommendRepositories(this.analyzer, category as string);
                res.json(recommendations);
            } catch (error) {
                res.status(500).json({ error: 'Failed to get recommendations' });
            }
        });

        // Add to learning path
        this.app.post('/api/github/learning/add', async (req, res) => {
            const { repo, category } = req.body;
            if (!repo || !category) {
                return res.status(400).json({ error: 'Missing required fields' });
            }

            this.learningManager.addToLearningPath(repo, category);
            res.json({ message: 'Added to learning path', path: category });
        });

        // Get learning path
        this.app.get('/api/github/learning/path', async (req, res) => {
            const { category } = req.query;
            const path = this.learningManager.getLearningPath(category as string);
            res.json({ path, categories: this.learningManager.getCategories() });
        });

        return this.app;
    }

    listen(port: number) {
        this.app.listen(port, () => {
            console.log(`[GitHub Integration] Server running on port ${port}`);
        });
    }
}
