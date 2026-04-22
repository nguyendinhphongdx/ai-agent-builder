import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import Handlebars from 'handlebars';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class TemplateService implements OnModuleInit {
  private readonly logger = new Logger(TemplateService.name);
  private templates: Map<string, Handlebars.TemplateDelegate> = new Map();
  private readonly templatesDir: string;

  constructor() {
    this.templatesDir = path.join(__dirname, 'templates');
  }

  onModuleInit() {
    this.loadTemplates();
    this.registerHelpers();
  }

  private loadTemplates(): void {
    try {
      if (!fs.existsSync(this.templatesDir)) {
        this.logger.warn(`Templates directory not found: ${this.templatesDir}`);
        return;
      }

      const files = fs.readdirSync(this.templatesDir);

      for (const file of files) {
        if (file.endsWith('.hbs')) {
          const templateName = file.replace('.hbs', '');
          const templatePath = path.join(this.templatesDir, file);
          const templateContent = fs.readFileSync(templatePath, 'utf-8');

          this.templates.set(templateName, Handlebars.compile(templateContent));
          this.logger.log(`Loaded template: ${templateName}`);
        }
      }

      this.logger.log(`Loaded ${this.templates.size} templates`);
    } catch (error) {
      this.logger.error(`Failed to load templates: ${error}`);
    }
  }

  private registerHelpers(): void {
    Handlebars.registerHelper('currentYear', () => new Date().getFullYear());

    Handlebars.registerHelper('formatDate', (date: Date | string) => {
      const d = new Date(date);
      return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    });

    Handlebars.registerHelper('eq', (a: unknown, b: unknown) => a === b);
  }

  render(templateName: string, data: Record<string, unknown>): string {
    templateName = templateName || 'general';
    const template = this.templates.get(templateName);

    if (!template) {
      throw new Error(`Template not found: ${templateName}`);
    }

    return template(data);
  }

  hasTemplate(templateName: string): boolean {
    return this.templates.has(templateName);
  }

  getAvailableTemplates(): string[] {
    return Array.from(this.templates.keys());
  }
}
